# Phase 1 — AWS foundations and local readiness

Status: local setup verified. AWS cost settings, dedicated sandbox suitability, permanent root-key retirement, and conceptual assessment are not complete.

## Fundamentals and why they matter
- An AWS account is an ownership/billing/administrative boundary. A region is a geographic service scope; Availability Zones are isolated locations within a region.
- Authentication establishes who is making a request. Authorization determines permitted actions on resources.
- An IAM role has a trust policy controlling assumption and permission policies controlling actions. A user login is a separate identity from root.
- Temporary credentials expire. An ARN identifies a principal/resource; it is not a password.
- Docker's CLI asks an engine to run an image. On macOS, Docker Desktop runs the Linux engine in a VM. Containers use the image's Python, not the Mac's Python.
- A named volume retains PostgreSQL files when a container is replaced.

## What we did and verified
1. Checked Python, Node, Docker/Compose, and AWS CLI versions. Host Python originally reported 3.9.6; the later Python container reports 3.12.15. Node is 24.7.0. Docker CLI is 29.8.0; Compose is 5.5.1; AWS CLI is 2.37.6.
2. Diagnosed a missing Docker socket. Starting Docker Desktop restored CLI-to-engine connectivity. hello-world then executed successfully on ARM64.
3. Verified root MFA was already configured. Both root access keys were deactivated; one had been used for CLI EC2 access. Keys remain inactive, not deleted. Deactivation does not stop existing EC2 resources or charges.
4. Inspected IAM Identity Center. Organization creation warned of a Free-plan upgrade and immediate Free Tier credit expiry, so that route was not enabled. Standalone IAM console login plus aws login avoids requiring Organizations for this local project.
5. Preserved retail-student and its retail S3 policy. Enabled its MFA. Created separate aegis-dev with console access and MFA; intended policy is SignInLocalDevelopmentAccess. The full attachment list has not been independently verified.
6. Initial aws login selected the root browser session despite profile name aegis-dev. Logged out, signed in as the IAM user, replaced the profile session, and verified STS returned user/aegis-dev. Profile names are labels, not identities.
7. Billing screenshots showed the Free plan, remaining credits, and free access ending March 28, 2027 or upon credit exhaustion. October service-charge table showed $0.00; this does not prove zero usage or that resources are stopped.
8. Learner reports creating a budget. The actual amount, credits treatment, recipient, and thresholds remain unverified. Budget alerts are not themselves a hard spending cap. Preserve the Free plan; no cloud workload provisioning is authorized yet.
9. Started local PostgreSQL through Compose. Host port 5433 was occupied, so changed to 127.0.0.1:55432:5432. SQL returned database aegisops and PostgreSQL 17.11. Later Docker checks confirmed healthy status.
10. Corrected the empty .gitignore; .env is ignored and was not read. The later API slice uses a second ignored secret file, .env.api, for its restricted reader.

## Current local structure
- compose.yaml defines db and optional tools/queue/api services.
- backend contains monitoring, event, persistence, queue, and API modules developed in later slices.
- docs/PROGRESS.md is the current checkpoint; docs/UI-REQUIREMENTS.md preserves design standards.
- tests contains unit and isolated integration checks; frontend/infra are placeholders.

## Commands used
```sh
python3 --version
docker --version
docker compose version
node --version
aws --version
docker info
docker run --rm hello-world
docker run --rm python:3.12-slim python --version
aws login --profile aegis-dev
aws sts get-caller-identity --profile aegis-dev --no-cli-pager
docker compose up -d db
docker compose ps
docker compose exec db psql -U aegis_local -d aegisops -c "SELECT current_database(), version();"
```

## Troubleshooting lessons
- node -- version treats version as a script filename; node --version requests version information.
- Installed CLI does not prove a running Docker engine or working AWS authentication.
- A regular browser session and Incognito session can authorize different identities.
- Docker host and container ports are distinct; changing host port does not change PostgreSQL's internal port.
- Environment variables initialize a new PostgreSQL volume. Changing a local password file does not automatically change an already-initialized database password.

## Interview takeaways and open work
Explain principal verification, least privilege, temporary credentials, image/container/volume differences, and delayed cost data. Do not claim a dedicated sandbox exists: this account already contains retail-project resources. Root-key deletion, budget verification, live-resource inventory, spending authorization, and the Phase 1 quiz remain open. No application workload has been deployed to AWS.

## References
- https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user_manage_delete-key.html
- https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- https://aws.amazon.com/free/free-tier-faqs/
- https://hub.docker.com/_/postgres
