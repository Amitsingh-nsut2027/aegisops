"""Plan, deploy, or inspect the dedicated AWS static portfolio stack. Plan is default."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / ".local" / "portfolio-dist"
TEMPLATE = ROOT / "infra" / "aws" / "portfolio-template.json"
STACK = "aegisops-portfolio"
REGION = "us-east-1"


def is_protective_budget(budget: dict) -> bool:
    """Accept account-wide USD budgets; never mistake a service filter for coverage."""
    limit = budget.get("BudgetLimit", {})
    if (budget.get("BudgetType") != "COST" or budget.get("TimeUnit") != "MONTHLY" or
            limit.get("Unit") != "USD" or not 0 < float(limit.get("Amount", 0)) <= 5 or
            budget.get("CostFilters")):
        return False
    expression = budget.get("FilterExpression")
    if expression:
        # Current Budgets API replaces deprecated CostTypes with this expression.
        return (budget.get("Metrics") == ["UnblendedCost"] and expression == {
            "Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit"]}}})
    return budget.get("CostTypes", {}).get("IncludeCredit") is False


def is_early_actual_alert(notification: dict, budget: dict) -> bool:
    if (notification.get("NotificationType") != "ACTUAL" or
            notification.get("ComparisonOperator") != "GREATER_THAN"):
        return False
    threshold_type = notification.get("ThresholdType", "PERCENTAGE")
    if threshold_type not in ("PERCENTAGE", "ABSOLUTE_VALUE"):
        return False
    limit = 100 if threshold_type == "PERCENTAGE" else float(budget["BudgetLimit"]["Amount"])
    return 0 < notification.get("Threshold", 0) <= limit


def verify_artifact() -> dict:
    manifest = json.loads((ARTIFACT / "artifact-manifest.json").read_text())
    if manifest.get("kind") != "aegisops-public-artifact-v1":
        raise ValueError("Not a public portfolio artifact")
    expected = set(manifest["files"]) | {"artifact-manifest.json"}
    actual = {str(path.relative_to(ARTIFACT)) for path in ARTIFACT.rglob("*") if path.is_file()}
    if actual != expected or any(path.is_symlink() for path in ARTIFACT.rglob("*")):
        raise ValueError("Unexpected public files or symlinks")
    for name, digest in manifest["files"].items():
        path = (ARTIFACT / name).resolve()
        if not path.is_relative_to(ARTIFACT.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("Public artifact hash mismatch")
    data = json.loads((ARTIFACT / "demo-data.json").read_text())
    if data.get("kind") != "aegisops-portfolio-v1" or data.get("simulated") is not True:
        raise ValueError("Only synthetic portfolio data may be deployed")
    if "mode: 'portfolio'" not in (ARTIFACT / "runtime-config.js").read_text():
        raise ValueError("Refusing to deploy local API mode")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--profile", default="aegis-dev")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Create/update this dedicated static stack and upload fixtures")
    action.add_argument("--status", action="store_true", help="Read current deployment outputs")
    args = parser.parse_args()
    if not re.fullmatch(r"\d{12}", args.account_id):
        parser.error("account-id must contain 12 digits")
    bucket = f"aegisops-portfolio-{args.account_id}-{REGION}"
    if not args.apply and not args.status:
        manifest = verify_artifact()
        print(json.dumps({"mode": "plan_only", "network_calls": 0, "account": args.account_id,
                          "stack": STACK, "region": REGION, "bucket": bucket,
                          "resources": ["Private S3 bucket", "CloudFront OAC", "CloudFront distribution", "Scoped S3 bucket policy"],
                          "public_files": len(manifest["files"]) + 1,
                          "cost_estimate": str(ROOT / "infra/aws/COST-ESTIMATE.md"),
                          "teardown": str(ROOT / "infra/aws/DEPLOYMENT.md")}, indent=2))
        return

    def aws(*command, missing_ok=False):
        result = subprocess.run(["aws", *command, "--profile", args.profile, "--region", REGION,
                                 "--no-cli-pager", "--output", "json"], capture_output=True, text=True)
        if result.returncode:
            if missing_ok and "does not exist" in result.stderr:
                return None
            raise RuntimeError(result.stderr.strip())
        return json.loads(result.stdout) if result.stdout.strip() else {}

    identity = aws("sts", "get-caller-identity")
    if identity["Account"] != args.account_id or identity["Arn"].endswith(":root"):
        raise ValueError("Wrong account or root identity; deployment refused")
    current = aws("cloudformation", "describe-stacks", "--stack-name", STACK, missing_ok=True)
    if current:
        tags = {tag["Key"]: tag["Value"] for tag in current["Stacks"][0].get("Tags", [])}
        if tags.get("Project") != "AegisOpsPortfolio":
            raise ValueError("Existing stack is not tagged as this portfolio; deployment refused")
    if args.status:
        print(json.dumps(current or {"status": "not_deployed"}, indent=2))
        return
    manifest = verify_artifact()
    plan = aws("freetier", "get-account-plan-state")
    credits = plan.get("accountPlanRemainingCredits", {})
    if (plan.get("accountId") != args.account_id or plan.get("accountPlanType") != "FREE" or
            plan.get("accountPlanStatus") != "ACTIVE" or credits.get("unit") != "USD" or
            credits.get("amount", 0) < 5):
        raise ValueError("Require an active FREE account plan with at least $5 credit reserve; no plan upgrade is performed")
    budgets = aws("budgets", "describe-budgets", "--account-id", args.account_id)
    matching_budgets = [b for b in budgets.get("Budgets", []) if is_protective_budget(b)]
    if not matching_budgets:
        raise ValueError("A monthly account-wide cost budget of $5 or less, excluding credits, must be verified first; alerts are not a hard cap")
    notified = False
    for budget in matching_budgets:
        notifications = aws("budgets", "describe-notifications-for-budget", "--account-id", args.account_id,
                            "--budget-name", budget["BudgetName"])
        for notification in notifications.get("Notifications", []):
            if not is_early_actual_alert(notification, budget):
                continue
            subscribers = aws("budgets", "describe-subscribers-for-notification", "--account-id", args.account_id,
                              "--budget-name", budget["BudgetName"], "--notification", json.dumps(notification))
            notified |= any(item.get("SubscriptionType") == "EMAIL" for item in subscribers.get("Subscribers", []))
    if not notified:
        raise ValueError("Require an actual-spend budget alert with an email subscriber before deployment; confirm recipient verification in the AWS console")
    aws("cloudformation", "validate-template", "--template-body", "file://" + str(TEMPLATE))
    operation = "update-stack" if current else "create-stack"
    try:
        aws("cloudformation", operation, "--stack-name", STACK, "--template-body", "file://" + str(TEMPLATE),
            "--tags", "Key=Project,Value=AegisOpsPortfolio")
        print("Waiting for the dedicated portfolio stack…", flush=True)
        aws("cloudformation", "wait", "stack-update-complete" if current else "stack-create-complete", "--stack-name", STACK)
    except RuntimeError as error:
        if not (current and "No updates are to be performed" in str(error)):
            raise
    deployed = aws("cloudformation", "describe-stacks", "--stack-name", STACK)["Stacks"][0]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in deployed["Outputs"]}
    if outputs["BucketName"] != bucket:
        raise ValueError("Unexpected upload destination")
    # Upload manifest last. Never read .env, AWS files, DB rows, or the source checkout here.
    for name in [*manifest["files"], "artifact-manifest.json"]:
        aws("s3", "cp", str(ARTIFACT / name), f"s3://{bucket}/{name}", "--cache-control", "public,max-age=60", "--only-show-errors")
    invalidation = aws("cloudfront", "create-invalidation", "--distribution-id", outputs["DistributionId"], "--paths", "/*")
    aws("cloudfront", "wait", "invalidation-completed", "--distribution-id", outputs["DistributionId"],
        "--id", invalidation["Invalidation"]["Id"])
    (ROOT / ".local" / "portfolio-deployment.json").write_text(json.dumps(outputs, indent=2))
    print(json.dumps({"status": "deployed", **outputs}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, KeyError, OSError) as error:
        raise SystemExit(str(error)) from None
