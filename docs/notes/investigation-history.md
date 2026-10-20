# Investigation history — persistence and authenticated reads

## What changed
The investigator now appends its completed report to PostgreSQL and prints `persisted: true` only after the transaction commits. The HTTP API exposes saved reports to the local viewer role. Earlier reports printed before this feature were not stored and are not backfilled.

The workflow still uses the fake provider, simulated CPU evidence, and needs_evidence outcome. This step adds storage and visibility, not additional evidence or real model reasoning.

## Run and inspect
From the project root:
```sh
python3 scripts/init_local_env.py
docker compose build investigator
docker compose run --rm investigator
docker compose --profile api up -d api
python3 scripts/create_viewer_token.py
```

The initializer preserves existing secrets and creates the new ignored, private .env.investigator file if missing. Compose first applies migrations and configures the dedicated roles. Do not share secret/token files.

At http://127.0.0.1:8000/docs, authorize ViewerJWT with the private token in .local/viewer-token.txt. Execute GET /investigations with limit=2, optionally filtering by event_id. Copy a run_id to GET /investigations/{run_id}. An expired or missing token returns 401. An unassigned role is denied by the investigations:read permission check. No HTTP report-creation route exists.

## Storage model
Alembic revision 0002_investigation_runs adds:

| Column | Purpose |
|---|---|
| run_id | Primary key; one invocation's identity |
| event_id | Foreign key to the saved source event |
| state | Currently constrained to needs_evidence |
| started_at / finished_at | UTC workflow execution times; finish cannot precede start |
| payload | JSONB snapshot of the report, evidence inventory, provider metadata, and trace |

An index supports per-event history. Lists sort by started_at descending and run_id ascending, with limit+1 to detect another page. Limit is 1–100 and offset is 0–10000. Offset pagination can shift when new runs arrive; snapshot/cursor pagination is future work. Both list and detail currently return the full report payload, suitable for this small local dataset; compact list projections and payload-size limits remain future work.

## Identity and replay
The source event ID remains stable. Each investigator invocation creates a new run ID and appends a new report, even for the same event. Inserting an existing run ID raises a primary-key conflict instead of overwriting history. There is no durable job ID or retry policy for an uncertain commit: if the database commits but the process loses the response, an operator can inspect history before starting another run. These are append-only snapshots, not resumable workflow state.

## Database privileges
| Role | Source events | Investigation runs |
|---|---|---|
| aegis_api | SELECT | SELECT |
| aegis_investigator | SELECT | SELECT, INSERT |
| local migration administrator | Schema/role administration | Schema/role administration |

The investigator receives INVESTIGATOR_PASSWORD from .env.investigator. The API receives its separate reader password and JWT key. Neither runtime service receives the migration administrator's password. The setup job receives administrator and role passwords to provision them; it does not print their values.

The investigator cannot update or delete events or reports. The API cannot insert reports, even after disabling its default read-only transaction setting. Startup checks verify the expected principal and relevant table privileges. This is a local permission boundary, not cryptographic tamper evidence: an administrator can still modify data. The schema stores JSONB snapshots from the trusted workflow, without database checks for every nested payload field. Production needs retention, backup/restore validation, stricter report contracts, and audit controls.

## Failure behavior
- Invalid/missing source event: no report is generated or saved.
- Provider failure: the existing deterministic fallback is recorded and can be saved.
- Save failure: transaction rolls back; the CLI exits with a generic error instead of claiming persisted success.
- Duplicate run ID: rejected; history is never overwritten by this writer.
- Unknown API run ID: 404; malformed ID or pagination: 422.
- Database unavailable: API returns sanitized 503.

## Verification
49 unit tests passed. Three writer integration tests checked an actual JSONB round trip, duplicate primary-key rejection, source-event foreign key, and denied event/history mutations. Four API reader integration tests passed, including denied history INSERT/DELETE with read-only transaction mode disabled. Integration test inserts were rolled back. One intentional demonstration report was committed. Live API checks verified readiness, 401 without a token, authenticated list/detail and event filtering, missing ID 404, and invalid limit 422.

## Interview explanation
“I separated stable source events from per-invocation investigation history. Each report is an append-only PostgreSQL snapshot tied to an existing event by a foreign key. The investigator has a dedicated insert-capable role, while the HTTP API remains SELECT-only and checks a viewer JWT permission. Transactions commit before we report persistence success. Replay creates another investigation run rather than overwriting prior history. The current analysis is explicitly simulated.”
