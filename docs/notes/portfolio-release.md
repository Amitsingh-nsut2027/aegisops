# Public portfolio release

The user selected a public portfolio demo while keeping Python/PostgreSQL local, and then chose AWS using existing credits. This narrows deployment scope: no real AI claims, no public API/database, and no account-plan upgrade.

## Architecture

```text
Build: scripted CPU inputs → canonical detector/events → fake investigator → allowlisted artifact
Public: browser → HTTPS CloudFront → OAC-signed private S3 → static screens + demo-data.json
Local: browser → loopback JWT bridge → FastAPI → PostgreSQL (unchanged)
```

frontend/runtime-config.js defaults to local mode. scripts/build_portfolio.py creates a separate portfolio-configured copy under .local/portfolio-dist. It copies an explicit frontend file list and licensed fonts, generates 14 synthetic events and 33 fake-provider reports without DB access, and writes file hashes. frontend/data-client.js selects the same-origin API in local mode or the single public fixture file in portfolio mode. The fixture client supports list/detail, exact filters, sort/pagination, missing rows, and mutation isolation. No live stream is fabricated.

The persistent public notice identifies scripted CPU incidents, fake provider, and no live AWS monitoring/model calls. This is an adaptation of the two approved screens, not a new unapproved screen. Dynamic execution timing comes from local report generation; observation timestamps are synthetic and labeled. No account IDs or private logs are exported.

## Deployment and security
See ../../infra/aws/DEPLOYMENT.md and COST-ESTIMATE.md. The guarded script verifies exact artifact contents and hashes before upload. The S3 origin blocks public access and grants CloudFront reads only for this distribution's SourceArn. CloudFront uses HTTPS redirects and managed security headers; the HTML includes CSP. No IAM resources, compute, DB, model, or custom domain is provisioned. A dedicated stack tag and bucket name separate the demo from existing retail resources.

The account owner explicitly approved the account-specific managed policy creation and attachment. The assistant completed it through the root console, then resumed deployment checks as aegis-dev. IAM validation and credit-plan/budget reads succeed. Budget email verification is pending. No deployment success can be claimed until the stack, upload, invalidation, and live URL all succeed.

## Validation
87 backend/release tests pass with Docker networking disabled; 10 frontend unit checks pass. Public-mode unit tests verify no API calls, pagination, exact identity/filter behavior, cloned return values, failure retry, and unchanged local error forwarding. Release checks reject extra private files and hash tampering and assert the private-origin resource set and policy scope. A basic scan found no key/JWT/account ID/private source path patterns; this is a scoped check, not a universal secret-detection guarantee.

Browser checked 14 incident rows, 25/8 history pagination across 33 runs, selected report and Trace view, fonts referenced from local assets, and no document-width overflow at 1280/1024/768/390. Actual captures live in ../design/review-portfolio. The broader earlier exceptional-state browser suites were not fully rerun for this release adaptation. Backend read integration and real AWS policy/template behavior remain separate checks.

## Interview framing
Say “I built a local incident-processing backend and an AWS-hosted scripted portfolio workbench” only after hosting succeeds. Do not say that the public demo monitors real AWS, performs autonomous remediation, or proves real-model accuracy. The currently incomplete roadmap is recorded in PROGRESS.md.

### CloudFront account verification blocker — 2026-10-19
The user reports budget email verification completed. The console subsequently uses the restricted aegis-dev session and cannot independently refresh that status. Renewed CLI identity is verified as aegis-dev. Deployment preflight and AWS template validation passed. CloudFormation created the private portfolio bucket and origin access control, but CloudFront refused distribution creation because the AWS account requires verification through AWS Support (403, request 1132be57-5151-44be-ad6f-114a2dbaee45). Automatic rollback began. No files were uploaded and no public URL is live. See infra/aws/CLOUDFRONT-VERIFICATION.md for the unsent support draft and resume steps.

Cleanup verified: CloudFormation is ROLLBACK_COMPLETE; PortfolioBucket, PortfolioOriginAccess, and PortfolioDistribution show DELETE_COMPLETE. No portfolio hosting resources remain from this attempt. The empty failed-stack record is retained for diagnosis.

## Successful public release — 2026-10-19
Supersedes earlier pending deployment and rollback states. AWS Support confirmed CloudFront verification. Retried as aegis-dev after removing the empty rolled-back stack record. Stack CREATE_COMPLETE, 16-file upload and invalidation completed. Live: https://d2mmk7avpz0dbe.cloudfront.net . Public content hashes, matching manifest, protected origin, blocked API/secret paths, incident selection/trace, 25+8 history pagination, command palette, and mobile fit verified. Backend remains local and public mode makes no model calls. Read docs/notes/deployed-portfolio.md for interview notes, resources, cost limits, and validation evidence.
