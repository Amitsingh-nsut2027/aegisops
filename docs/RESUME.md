# AegisOps — resume and interview notes

Live demo: https://d2mmk7avpz0dbe.cloudfront.net
Source: https://github.com/Amitsingh-nsut2027/aegisops

## Suggested resume entry

**AegisOps — Incident Investigation Workbench** | Python, FastAPI, PostgreSQL, Docker, AWS S3/CloudFront

- Built a CPU-alert processing pipeline with deterministic event identities, validated queue messages, and idempotent PostgreSQL persistence; acknowledged messages only after transaction commit.
- Developed an interactive investigation workbench with evidence inventories, saved report history, execution traces, revisioned runbook excerpts, and local JWT-protected read APIs.
- Published a labelled simulation demo through CloudFront with a private S3 origin, CloudFormation infrastructure, scoped deployment permissions, and hash-verified release artifacts.

Use two bullets if space is limited. Link the project name to the repository and add a separate “Live demo” link. No invented uptime, scale, accuracy, or recovery-time metrics.

## A 45-second explanation

“AegisOps helps an operator inspect a CPU alert and the evidence behind an investigation. I separated deterministic detection from queue delivery and database persistence. Stable event identities prevent duplicate rows on replay, and messages are acknowledged after commit. Each investigation saves its own evidence inventory, validated summary, workflow trace, and runbook excerpts. I built a read-only workbench for those records and deployed a separate simulation demo with CloudFront and a private S3 origin. The full backend runs locally; the public demo uses scripted fixtures and makes no model or infrastructure-change calls.”

## Demo walkthrough

1. Open Incidents, select orders-api, and explain the three-sample threshold window.
2. Compare saved runs: unavailable evidence is explicit rather than invented.
3. Open Trace: show recorded execution outcomes, not model chain-of-thought.
4. Open Runbooks: distinguish revisioned guidance from measured evidence.
5. Open RUN: reports are independent snapshots, while event IDs remain stable.
6. Explain the hosting boundary: static public demo versus authenticated local API.

## Questions to prepare

- What happens if a worker commits but fails before acknowledging a message?
- Why does high CPU not establish a root cause?
- How do HTTP viewer permissions differ from database role permissions?
- Why are observation timestamps different from report execution timestamps?
- What does the fake provider validate, and what would change with real inference?
- Why does private S3 behind CloudFront differ from a public bucket?
- What remains before this could be used in production?

The detailed answers are in INTERVIEW_QA.md and PROJECT_WALKTHROUGH.md. Do not claim live monitoring, real multi-agent investigation, production identity, or autonomous remediation. Those are not implemented in this release.
