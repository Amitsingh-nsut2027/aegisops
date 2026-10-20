# Phase 4 — Read-only FastAPI event API

Status: read-only API implemented and verified locally. Development JWT viewer authentication was added afterward; see phase-04-auth.md. Production identity integration, full workflow authorization, write endpoints, incident lifecycle, rate limiting, and other backend features remain pending.

## Fundamentals
HTTP is a request/response protocol. A client calls a route such as GET /events, and receives a status code plus JSON. FastAPI maps routes to Python functions, validates input with Pydantic, validates response contracts, and generates an OpenAPI specification plus interactive documentation.

A repository isolates SQL access from route behavior. SQLAlchemy builds parameterized statements; psycopg communicates with PostgreSQL. Lifespan setup creates the connection pool, verifies database privileges, and disposes the pool at shutdown. Synchronous handlers suit the current synchronous driver and run in FastAPI's thread pool.

## Why we need this
The eventual dashboard needs a bounded, predictable way to read incidents without accessing the database directly. This first API exposes the event journal, not yet a complete incident-management lifecycle. A read-only slice lets us build and verify HTTP contracts and privilege separation before adding mutations.

## Flow and files
```text
HTTP client → FastAPI validation → EventRepository → parameterized SELECT
                                                    ↓
                           JSON response ← PostgreSQL (aegis_api role)
```

| File | Responsibility |
|---|---|
| backend/api.py | App lifespan, routes, request IDs, JSON request logs, sanitized DB errors |
| backend/api_schemas.py | Explicit event/page response contracts |
| backend/event_repository.py | Bounded queries, readiness query, database-principal/privilege checks |
| backend/setup_api_role.py | Local administrator provisions the dedicated reader and its secret |
| backend/database.py | Shared engine factory; selects a password environment variable explicitly |
| scripts/init_local_env.py | Creates missing local secret files, preserving existing files without printing secrets |
| compose.yaml | One-off setup service and localhost-bound API service |
| tests/test_api.py | HTTP contract/failure unit tests using in-process TestClient |
| tests/integration/test_api_reader.py | Actual PostgreSQL reader permission checks |

## Routes
| Method and route | Behavior |
|---|---|
| GET /health | Process liveness; does not query the database |
| GET /ready | Checks access to the event table; 503 on database request failure |
| GET /events | Viewer JWT required; event page with optional source=simulator filter |
| GET /events/{event_id} | Viewer JWT required; one event by a 64-character lowercase hexadecimal ID |
| GET /docs | Interactive API reference |
| GET /openapi.json | Machine-readable API contract |

Page size defaults to 50 and is capped at 100; offset ranges from 0 to 10,000. Sort order is received_at descending then event_id ascending. We fetch one extra row to calculate has_more. This bounds the result and avoids a full count, but offset pages can shift under concurrent inserts. A cursor is a future improvement.

## Error and logging behavior
- Empty list: 200 with items=[] and has_more=false.
- Unknown but syntactically valid ID: 404.
- Invalid ID, query type/range, or unsupported source: 422 before querying the repository.
- SQLAlchemy database error during requests: generic 503; SQL, raw driver errors, and passwords are not returned.
- Unsupported POST /events: 405; no event write route exists.
- Each response includes a generated X-Request-ID and Cache-Control: no-store. Logs include method, path, status, duration, and request ID, excluding request bodies, query strings, headers, and secrets.
- Startup fails if the database is unavailable, schema absent, or principal/permissions are unsuitable. A successful /health is therefore not a substitute for readiness over the process lifetime.

## Privilege and secret model
api_setup uses the existing local administrator and runs the versioned migration before configuring aegis_api. API receives only DB_PASSWORD from ignored .env.api, not POSTGRES_PASSWORD. The role has LOGIN but no superuser, database-creation, role-creation, replication, or bypass-RLS capability; it receives schema USAGE and table SELECT. Its default transactions are read-only. API startup checks the principal and effective event-table read/write privileges.

The public schema's defaults do not grant this role CREATE; an integration test verifies that. A separate test changes a transaction to read/write and attempts DELETE ... WHERE false: PostgreSQL still denies it (SQLSTATE 42501). No rows are deleted by that test, even if a future privilege regression occurs. Default read-only mode is defense in depth, not the primary permission boundary.

Secrets are generated into mode-0600 files and not printed. Existing .env/.env.api files are preserved. Both are ignored by Git. The backend build context excludes .env files, and the API does not mount the repository or AWS credentials.

## Commands
Already configured on this computer. For initial setup from the project root:

```sh
python3 scripts/init_local_env.py
docker compose build api
docker compose --profile api up -d api
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
curl 'http://127.0.0.1:8000/events?limit=2&source=simulator'
```

Open http://127.0.0.1:8000/docs. Generate and authorize a viewer token using phase-04-auth.md before event requests; the curl event example without a header now intentionally receives 401. api_setup applies migration 0001 if missing, then configures the reader. If the database is empty, publish/process a simulation using the Phase 3 commands. Restarting the API does not seed extra events or change event rows.

Run unit tests:
```sh
docker compose run --rm --no-deps -v "$PWD/tests:/tests:ro" api python -B -m unittest discover -s /tests -v
```

Run actual database-role integration tests with API credentials:
```sh
docker compose run --rm --no-deps -v "$PWD/tests:/tests:ro" api python -B -m unittest discover -s /tests/integration -p test_api_reader.py -v
```

The queue integration tests must use the queue service instead; those require access to Moto. They are intentionally separate from the database-reader tests.

Stop all local services while preserving PostgreSQL data with `docker compose --profile api --profile queue down`. Moto's in-memory queues clear on restart. Never add -v to routine cleanup if the volume contains needed data.

## Verification results
- Initial slice: 22 unit tests passed (nine API, six monitoring, seven queue). JWT follow-up adds eight auth tests; total unit suite is now 30 and passed.
- Three actual PostgreSQL reader tests passed: read succeeds, write denied despite transaction-mode override, no schema CREATE.
- Live HTTP checks passed for health, readiness, filtered/paginated listing, detail, validation (422), missing item (404), and OpenAPI.
- Live listing returned four simulation events across the two existing demo scenarios.
- Earlier Phase 3 recorded three emulator integration tests for retry, acknowledgement, and DLQ behavior. These do not contact real AWS.
- Installed versions captured into requirements.txt; requirements.in retains direct ranges. Version snapshots are not hash-verified lockfiles.

## Known limits
Development JWT viewer checks are implemented; production login/identity-provider integration, full workflow RBAC, API rate limiting, TLS, live AWS data, and frontend are pending. Host binding is 127.0.0.1:8000; do not publish this development API as-is. Local importer/worker roles still use the administrator; introduce a restricted runtime writer before public deployment. Current API schemas expose only simulation records. Tests use unittest for now; planned pytest/CI/tooling standardization remains open. The tested Starlette release emits a test-only deprecation warning for httpx-backed TestClient; update that dependency with the test-tooling split.

## Interview takeaways
Explain least privilege as permissions on the database, not simply a flag in Python. Distinguish liveness, readiness, input validation, response validation, and authorization. Demonstrate 401/403/404/422/503 behavior and request IDs. Explain the limited development JWT issuer separately from production identity management.

## Review questions (deferred)
1. Why does a read-only setting not replace SELECT-only grants?
2. If /health returns 200 and /ready returns 503, what would you inspect?
3. Why return 200 for an empty list but 404 for a missing detail resource?
4. What happens to offset pagination when newer events arrive between requests?
5. Why validate a page size before issuing SQL?
6. Why are the current SQL handlers synchronous?

## References
- https://fastapi.tiangolo.com/advanced/events/
- https://fastapi.tiangolo.com/tutorial/response-model/
- https://fastapi.tiangolo.com/tutorial/testing/
- https://www.postgresql.org/docs/17/sql-grant.html
