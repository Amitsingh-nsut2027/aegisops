# Cost and execution scope

The local backend and automated checks run without paid inference. The account owner separately authorized the static AWS portfolio release using existing credits.

- Public release: synthetic fixture files through private S3 and CloudFront HTTPS.
- Backend: local Docker services, PostgreSQL, Moto queue emulator, and read-only API.
- Investigation: deterministic fake provider; no paid model calls or live cloud monitoring.
- No account-plan upgrade, paid support subscription, cloud backend, or autonomous remediation is part of this release.

Publishing is explicit and defaults to offline planning. The deployer checks the non-root account identity, dedicated stack tags, artifact allowlist/hashes, Free-plan status, credit reserve, and budget configuration. Email verification requires a separate console check. Budget alerts do not guarantee a spending cap. Financial records and private deployment outputs stay outside Git.

See [cost assumptions](../infra/aws/COST-ESTIMATE.md), [deployment/teardown](../infra/aws/DEPLOYMENT.md), and [verified release scope](notes/deployed-portfolio.md).
