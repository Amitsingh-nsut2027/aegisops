# AegisOps AI — start here

Updated: 2026-10-19. These notes describe the current implementation, not just the final ambition.

## What you have built
A local event-processing backend that detects sustained high CPU in reproducible samples, creates evidence-bearing events, delivers them through an SQS-compatible test queue, stores them idempotently in PostgreSQL, and exposes them through a read-only FastAPI API.

The project also has a provider interface and a validated investigation demo using deterministic fake output. It does not yet call an LLM, monitor live AWS infrastructure, execute remediation, or have a frontend. Calling it a completed autonomous AWS SRE platform would overstate the current work.

The first investigator workflow now adds an evidence inventory, per-run identity, execution trace, and explicit needs_evidence outcome. Read [Phase 6](notes/phase-06-investigator.md) after the provider notes, then [investigation history](notes/investigation-history.md). Reports now persist in PostgreSQL and can be read through authenticated API endpoints.

Next read [simulated supplemental evidence](notes/simulated-evidence.md): explicitly generated demo context, provenance, event/resource/time scope, and citation validation. Real telemetry connectors remain future work.

Then read [local runbook retrieval](notes/local-runbooks.md): bounded knowledge lookup, relevance scores, revisioned excerpts, and the distinction between guidance and observed evidence.

The binding [design contract](../DESIGN.md) governs typography, colors, interactions, per-screen approval, critique, and polish. The user approved screen one, which is now a working [incident workbench](notes/frontend-workbench.md). Start it with `python3 scripts/start_workbench.py`. Later screens still need their own approved wireframes; earlier static preview images remain superseded.

The separately approved [Investigation history screen](notes/frontend-investigations.md) is also implemented. Choose RUN to inspect saved executions independently of source events, with exact event filtering, preserved old snapshots, and precise workflow timing. Its own critique and polish evidence are separate from screen one.

## Read in this order
1. [Project walkthrough](PROJECT_WALKTHROUGH.md): follow one event from a CPU sample to an HTTP response. Start with this before looking at code.
2. [Phase 1](notes/phase-01-foundations.md): Docker, identities, local database, and account/cost status.
3. [Phase 2](notes/phase-02-monitoring.md): threshold detection, state, simulation, and event identity.
4. [Local persistence](notes/local-persistence.md): schema migrations, transactions, and database-enforced idempotency.
5. [Phase 3](notes/phase-03-event-queue.md): producer, queue, worker, retries, and dead-letter messages.
6. [Phase 4](notes/phase-04-api.md): HTTP endpoints, validation, database permissions, and failure responses.
7. [Local JWT authentication](notes/phase-04-auth.md): signing, claims, viewer permissions, and development limitations.
8. [Phase 5 provider foundation](notes/phase-05-provider.md): provider contracts, structured output, bounded repair, fallback, and simulation limits.
9. [Interview Q&A](INTERVIEW_QA.md): practice explaining decisions in your own words.
10. [Progress](PROGRESS.md): verified work, unresolved items, and next checkpoint.
11. [UI requirements](UI-REQUIREMENTS.md): standing frontend design standards and approval process.

## How to study each feature
For every module, answer: what enters it, what comes out, what state it owns, what happens on failure, and how we verified it. Read the relevant test next to the implementation. Memorizing commands alone will not prepare you to defend the architecture.

## A short demo
The containers are already configured on this computer. From the repository root:

```sh
docker compose --profile api up -d api
docker compose run --rm queue python queue_demo.py publish --scenario-id queue-demo-v1
docker compose run --rm queue python queue_demo.py work
python3 scripts/create_viewer_token.py
```

Open http://127.0.0.1:8000/docs, authorize ViewerJWT with the private token from .local/viewer-token.txt, then execute GET /events with limit=2. A direct unauthenticated request now returns 401. Publishing the already-stored queue-demo-v1 scenario should produce duplicates, not extra rows. For a new intentional simulation, choose a new scenario ID. Moto queues are volatile; restart and republish if needed. PostgreSQL data is stored in a named volume.

For a fresh checkout, first run `python3 scripts/init_local_env.py`, build the backend image, and follow the startup commands in the Phase 4 notes. Do not regenerate an existing database's lost administrator password and expect it to match the volume; preserve or recover the original secret.

## How notes will evolve
Each new slice records fundamentals, purpose, files, decisions and alternatives, commands, failure behavior, verification, limitations, and interview takeaways. Completed checkpoints are distinct from planned capabilities. Questions are for review; the learner requested that quiz pauses be deferred while building.

## Bedrock adapter preparation
Read [Phase 5: offline Bedrock adapter](notes/phase-05-bedrock-adapter.md) for provider translation, SDK contract tests, completion validation, and what remains before live inference.

Read [provider usage accounting](notes/provider-usage-accounting.md) for retry totals, missing telemetry, and the free-only development boundary.
