# Static portfolio deployment

Live release: https://d2mmk7avpz0dbe.cloudfront.net

This hosts only the scripted portfolio. The Python/PostgreSQL backend stays local. The template provisions a private S3 bucket, origin access control, a tagged CloudFront distribution, and its scoped bucket policy. It creates no IAM roles, compute, database, or model endpoints.

## Before publishing

Use a non-root AWS identity in your own account. The example `portfolio-deployer-policy.json` uses **111122223333**, a documentation account ID: replace it with your account ID before reviewing and attaching a customer-managed policy. Never attach it unchanged or broaden it to AdministratorAccess to bypass an error. It is above the aggregate IAM user inline-policy size limit.

CloudFormation access is scoped to the `aegisops-portfolio` stack in `us-east-1`; S3 access is scoped to the account-specific portfolio bucket. CloudFront creation requires a Project=AegisOpsPortfolio request tag; subsequent distribution management requires that resource tag. Some origin access control and managed-policy reads use wildcard resources because their authorization model requires it. The policy grants no IAM, EC2, RDS, Bedrock, account-upgrade, or unrelated bucket access.

The deployer requires an ACTIVE FREE account plan, at least $5 USD remaining credits, and an account-wide monthly cost budget at $5 or less that excludes credits. Add an actual-spend email alert at or below the budget amount. Confirm the recipient is Verified in the AWS budget console: merely appearing in the CLI subscriber list does not prove verification. Budgets are delayed warnings, not spending caps. A PAID plan is rejected under the current credit-only deployment policy.

If AWS refuses CloudFront creation pending account verification, use account/billing support. Do not try to resolve an account restriction by granting broader IAM access or upgrading a support plan. See [verification history](CLOUDFRONT-VERIFICATION.md).

## Build the isolated public artifact

From the project root:

```sh
docker build -t aegisops-backend:local backend
docker run --rm --network none --user "$(id -u):$(id -g)" \
  -v "$PWD:/workspace" -w /workspace aegisops-backend:local \
  python -B scripts/build_portfolio.py
python3 -m http.server 5174 --bind 127.0.0.1 --directory .local/portfolio-dist
```

Preview localhost:5174, then stop the preview with Ctrl+C. This static preview needs no local database or AWS credentials. It does not replace the authenticated local workbench on port 5173.

The builder generates synthetic events and calls the local deterministic provider workflow. It never copies local database rows, secrets, or the backend into the release. The explicit file allowlist and SHA-256 manifest protect the upload boundary.

## Plan and publish

These examples use a documentation account ID; supply your own ID for deployment. Plan is offline and creates nothing:

```sh
python3 scripts/deploy_portfolio.py --account-id 111122223333
```

After reviewing the plan, permissions, cost assumptions, and verified budget alert:

```sh
python3 scripts/deploy_portfolio.py --account-id 111122223333 --apply
python3 scripts/deploy_portfolio.py --account-id 111122223333 --status
```

Default profile: `aegis-dev`. Region: `us-east-1`. Stack: `aegisops-portfolio`. The script verifies identity, account plan, budget, existing stack tag, portfolio mode, and artifact hashes before template validation and mutation. It waits for CloudFormation, uploads only manifest-listed files, invalidates the distribution, waits for invalidation completion, then records outputs privately in `.local/portfolio-deployment.json`.

A rolled-back failed stack cannot be updated. Inspect its events and resources, confirm cleanup, and remove only the empty failed-stack record before retrying creation. A failure must be resolved explicitly; a partial stack is not a successful deployment.

## Teardown

Use your own account-specific bucket and distribution from the saved outputs. Verify the account, exact stack tags, and resources first. Empty only that portfolio bucket, delete the portfolio stack, and wait for deletion to complete. Do not target unrelated buckets or rely on deleting the local output file to remove AWS resources.

```sh
aws sts get-caller-identity --profile aegis-dev --no-cli-pager
aws cloudformation describe-stacks --stack-name aegisops-portfolio --region us-east-1 --profile aegis-dev --no-cli-pager
aws s3 rm s3://aegisops-portfolio-111122223333-us-east-1 --recursive --profile aegis-dev
aws cloudformation delete-stack --stack-name aegisops-portfolio --region us-east-1 --profile aegis-dev
aws cloudformation wait stack-delete-complete --stack-name aegisops-portfolio --region us-east-1 --profile aegis-dev
```

These examples delete data and infrastructure when substituted with real identifiers. CloudFormation removes its distribution, origin access control, bucket policy, and the empty bucket. Inspect deletion failures before assuming costs have stopped. Remove the deployment policy if further publishing is not needed.

## Verified release

The current public release reached CREATE_COMPLETE, uploaded 16 files, completed invalidation, and passed live interaction, file-hash, HTTP redirect, security-header, and private-origin checks. See [deployment evidence](../../docs/notes/deployed-portfolio.md).
