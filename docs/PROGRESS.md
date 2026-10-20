# Implemented milestones and open work

Current release: [public portfolio demo](https://d2mmk7avpz0dbe.cloudfront.net), with the full Python/PostgreSQL backend running locally.

## Implemented

1. Deterministic CPU episode detection, replay-stable event IDs, structured CPU evidence, and strict event validation.
2. PostgreSQL event journal, Alembic migrations, idempotent event inserts, commit-before-ack worker, Moto SQS-compatible queue and dead-letter behavior.
3. FastAPI read routes, bounded pagination, local 15-minute JWT viewer sessions, SELECT-only API database role, and database readiness checks.
4. Bounded fake-provider analysis with schema/citation validation, retries/fallback, an offline-tested Bedrock transport adapter, and per-attempt usage accounting without fabricated token counts.
5. Fixed investigation workflow, evidence inventory, scripted supplemental evidence, persisted independent report snapshots, revisioned tag-selected runbook excerpts, and execution traces.
6. Two interactive frontend screens: incidents and investigation history. Keyboard navigation/palette, copy actions, filtering, saved-run selection, resizable inspector, and mobile detail navigation.
7. Synthetic public artifact with 14 incidents and 33 reports, explicit simulation provenance, isolated static data client, file allowlist and SHA-256 manifest.
8. CloudFormation deployment through a scoped non-root identity to private S3 and CloudFront. Account verification resolved through AWS Support; failed-attempt rollback confirmed before retry. Live release verified.
9. Recruiter-oriented README, setup/architecture documentation, GitHub checks workflow, and accurate resume/interview notes.

## Verification on 2026-10-20

- 90 backend/release unit and contract tests passed with container networking disabled.
- 10 frontend data/format tests and module syntax checks passed.
- 4 actual PostgreSQL read-role integration tests passed.
- Live artifact hashes, matching manifest, HTTPS redirect/security headers, anonymous S3 denial, and unavailable API/secret paths verified during deployment.
- Public interaction checks cover event selection, report selector, tabs, history pagination, filter validation, copy feedback, command palette, and mobile detail/back navigation. Responsive artifact captures cover 1280, 1024, 768, and 390px.
- Local page recovery verified after stopping services: restart Docker/API/frontend and renew the viewer token. The local viewer session intentionally expires after 15 minutes. Localhost requires its services to remain running.

## Open work and claim boundaries

No live AWS telemetry collectors, real model invocation, autonomous multi-agent loop, production identity provider, approval/execution lifecycle, or remediation exist in this release. The Bedrock adapter is offline-tested, not proof of deployed inference. Runbooks are deterministic retrieved guidance rather than generated RAG answers. Public data is simulated, and local authentication is for development.

The visitor-introduction layout was proposed but has not been approved or implemented in the dashboard. The README now provides the project overview and demo walkthrough. No throughput, uptime, model accuracy, or recovery-time improvement has been measured.

Read [the project walkthrough](PROJECT_WALKTHROUGH.md), [release evidence](notes/deployed-portfolio.md), and [resume notes](RESUME.md).
