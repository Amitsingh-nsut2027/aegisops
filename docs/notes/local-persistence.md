# Local incident persistence

## Concepts and data flow
Fixed CPU samples → deterministic detector → structured simulated events → SQLAlchemy insert → PostgreSQL event journal.

- SQLAlchemy constructs parameterized SQL; psycopg is the PostgreSQL driver.
- Alembic records schema versions and applies migrations independently of imports.
- A transaction commits the event batch together or rolls it back on failure.
- event_id is the primary key; PostgreSQL ON CONFLICT DO NOTHING prevents duplicate rows on replay, including concurrent insert attempts.
- observed_at is synthetic scenario time; received_at is actual database receipt time. Simulator events are explicitly labeled.
- This is an event journal, not a complete incident lifecycle, queue, or agent system.

## Files
- backend/database.py: connection factory and table metadata.
- backend/persist_incidents.py: transactional repository function and demo importer.
- backend/migrations/: versioned schema history.
- backend/Dockerfile: non-root local importer with pinned base digest.
- backend/requirements.in: direct dependency constraints.
- backend/requirements.txt: exact direct/transitive versions captured from the tested Python 3.12 image. Update deliberately and rebuild/retest; this is a version snapshot, not a hash-verified lockfile.
- compose.yaml: optional tools-profile ingest service connected to db over the Compose network.

## Commands (project root)
```sh
docker compose build ingest
docker compose run --rm ingest alembic upgrade head
docker compose run --rm ingest
docker compose run --rm ingest
docker compose exec -T db psql -U aegis_local -d aegisops -c "SELECT source, event_type, COUNT(*) FROM incident_events GROUP BY source, event_type;"
```

On a fresh database the importer inserts two events; replay inserts zero and reports two duplicates. Other scenarios may increase the total count. Repeated IDs do not replace stored payloads.

Stop local services with docker compose down; retain the database volume. Migration downgrade drops this table and its records, so it is not a routine teardown command.

## Security and limits
- No AWS resources or credentials involved.
- Password comes from the existing ignored .env at container runtime; it is neither embedded in the image nor logged by our code.
- Importer connects to db:5432 internally; host tools use 127.0.0.1:55432.
- This local migration/import exercise uses the existing local database administrator. Separate migration-owner and restricted runtime roles are required before an externally accessible API or cloud deployment.
- App-level event validation at untrusted boundaries, retries, migrations in CI, persistent streaming state, and collision/payload mismatch handling remain future work.

## Validation
Initial migration applied successfully to the local database. First import generated 2/inserted 2; replay generated 2/inserted 0/duplicates 2. No destructive downgrade or existing table modification performed.

## Interview takeaway
Idempotency must be enforced in the database. Checking for existence before inserting alone can race when two workers process the same event.
