import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class PortfolioReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("portfolio_deploy", ROOT / "scripts/deploy_portfolio.py")
        cls.deploy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.deploy)

    def artifact(self, directory):
        files = {"runtime-config.js": "export const runtime = {mode: 'portfolio'};",
                 "demo-data.json": json.dumps({"kind": "aegisops-portfolio-v1", "simulated": True})}
        hashes = {}
        for name, text in files.items():
            (directory / name).write_text(text)
            hashes[name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
        (directory / "artifact-manifest.json").write_text(json.dumps({"kind": "aegisops-public-artifact-v1", "files": hashes}))

    def test_manifest_accepts_only_exact_unchanged_public_files(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.artifact(directory)
            with patch.object(self.deploy, "ARTIFACT", directory):
                self.deploy.verify_artifact()
                (directory / ".env").write_text("not-a-real-secret")
                with self.assertRaisesRegex(ValueError, "Unexpected public files"):
                    self.deploy.verify_artifact()

    def test_tampering_is_rejected_before_aws_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            self.artifact(directory)
            (directory / "runtime-config.js").write_text("local")
            with patch.object(self.deploy, "ARTIFACT", directory), self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.deploy.verify_artifact()

    def test_template_keeps_s3_private_and_scopes_read_grant_to_one_distribution(self):
        template = json.loads((ROOT / "infra/aws/portfolio-template.json").read_text())
        resources = template["Resources"]
        self.assertEqual({item["Type"] for item in resources.values()}, {
            "AWS::S3::Bucket", "AWS::S3::BucketPolicy", "AWS::CloudFront::OriginAccessControl", "AWS::CloudFront::Distribution"})
        self.assertTrue(all(resources["PortfolioBucket"]["Properties"]["PublicAccessBlockConfiguration"].values()))
        policy = resources["PortfolioBucketPolicy"]["Properties"]["PolicyDocument"]["Statement"][0]
        self.assertEqual(policy["Principal"], {"Service": "cloudfront.amazonaws.com"})
        self.assertIn("PortfolioDistribution", policy["Condition"]["StringEquals"]["AWS:SourceArn"]["Fn::Sub"])
        distribution = resources["PortfolioDistribution"]["Properties"]["DistributionConfig"]
        self.assertEqual(distribution["DefaultCacheBehavior"]["ViewerProtocolPolicy"], "redirect-to-https")
        self.assertEqual(distribution["DefaultCacheBehavior"]["AllowedMethods"], ["GET", "HEAD"])

    def test_deployer_policy_has_no_iam_compute_model_or_retail_permissions(self):
        policy = json.loads((ROOT / "infra/aws/portfolio-deployer-policy.json").read_text())
        for statement in policy["Statement"]:
            actions = statement["Action"]
            for action in [actions] if isinstance(actions, str) else actions:
                self.assertNotIn(action.split(":")[0], ["iam", "ec2", "bedrock", "rds"])
                self.assertNotEqual(action, "*")
        self.assertNotIn("retail", json.dumps(policy))

    def test_budget_accepts_legacy_and_current_explicit_credit_exclusion(self):
        budget = {"BudgetType": "COST", "TimeUnit": "MONTHLY",
                  "BudgetLimit": {"Amount": "5.0", "Unit": "USD"},
                  "CostTypes": {"IncludeCredit": False}}
        self.assertTrue(self.deploy.is_protective_budget(budget))
        del budget["CostTypes"]
        self.assertFalse(self.deploy.is_protective_budget(budget))
        budget.update(Metrics=["UnblendedCost"], FilterExpression={
            "Not": {"Dimensions": {"Key": "RECORD_TYPE", "Values": ["Credit"]}}})
        self.assertTrue(self.deploy.is_protective_budget(budget))
        budget["FilterExpression"] = {"Dimensions": {"Key": "SERVICE", "Values": ["Amazon S3"]}}
        self.assertFalse(self.deploy.is_protective_budget(budget))

    def test_budget_rejects_wrong_currency_large_limit_and_partial_scope(self):
        budget = {"BudgetType": "COST", "TimeUnit": "MONTHLY",
                  "BudgetLimit": {"Amount": "5", "Unit": "USD"},
                  "CostTypes": {"IncludeCredit": False}}
        for change in ({"BudgetLimit": {"Amount": "5", "Unit": "EUR"}},
                       {"BudgetLimit": {"Amount": "50", "Unit": "USD"}},
                       {"CostFilters": {"Service": ["Amazon S3"]}},
                       {"TimeUnit": "ANNUALLY"}):
            self.assertFalse(self.deploy.is_protective_budget({**budget, **change}))

    def test_alert_supports_omitted_percentage_type_and_rejects_late_thresholds(self):
        budget = {"BudgetLimit": {"Amount": "5"}}
        notification = {"NotificationType": "ACTUAL", "ComparisonOperator": "GREATER_THAN", "Threshold": 50.0}
        self.assertTrue(self.deploy.is_early_actual_alert(notification, budget))
        self.assertFalse(self.deploy.is_early_actual_alert({**notification, "Threshold": 150}, budget))
        self.assertFalse(self.deploy.is_early_actual_alert({**notification, "NotificationType": "FORECASTED"}, budget))
        self.assertFalse(self.deploy.is_early_actual_alert({**notification, "ThresholdType": "ABSOLUTE_VALUE"}, budget))
        self.assertTrue(self.deploy.is_early_actual_alert({**notification, "ThresholdType": "ABSOLUTE_VALUE", "Threshold": 2.5}, budget))
