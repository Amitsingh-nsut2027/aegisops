# Interview Q&A — implemented foundation

These model answers are grounded in current work. Practice explaining them without memorizing exact wording. AI-agent/RAG/remediation questions will be added when those features exist.

## 1. What does your project currently do?
It detects sustained CPU threshold breaches in deterministic simulations, builds evidence-bearing events, sends them through a local SQS-compatible queue, processes them into PostgreSQL without duplicate rows, and exposes a read-only HTTP API. It is the foundation of a planned AI-assisted AWS incident-response system.

## 2. Why does the detector not use an LLM?
Threshold comparison is explicit arithmetic and state. Ordinary code is cheaper, deterministic, and easier to test. LLM reasoning will be useful later for synthesizing logs, changes, and runbooks into hypotheses.

## 3. Why require three consecutive high readings?
It filters isolated spikes. The trade-off is slower detection. The correct window depends on the service SLO and sampling frequency; three readings is a teaching configuration, not a universal SRE recommendation.

## 4. What is the difference between an alert and a root cause?
An alert reports a symptom such as sustained CPU. A root-cause hypothesis explains it using supporting and conflicting evidence. High CPU alone does not prove a bad deployment or traffic spike.

## 5. How do you avoid repeat alerts?
The batch detector tracks a high-reading streak and whether the current episode has already alerted. A normal reading resets both. State across independent calls is not yet persisted.

## 6. Why use a queue?
The producer can publish independently of worker execution, and failures can be retried. Queues also introduce redelivery and backlog management. Our local emulator demonstrates the processing model, while production durability still requires actual AWS verification.

## 7. What is a visibility timeout?
After receipt, a message is temporarily hidden from other receives. If it is not acknowledged, it becomes available again. Our demo uses 30 seconds and processes one batch per invocation; long jobs will need visibility extension later.

## 8. Why acknowledge after the database commit?
Acknowledging first risks permanent loss if the database write then fails. Committing first can cause duplicate delivery after a crash, which we handle through a unique event ID and an idempotent insert.

## 9. What happens if the worker crashes immediately after committing?
The message may be delivered again. The second insert conflicts with the existing primary key and adds no row. The worker can acknowledge that duplicate safely.

## 10. Is this exactly-once processing?
No. Delivery may happen more than once. We prevent duplicate event rows for the same ID. That does not guarantee exactly-once external AWS actions, which will need their own execution records, idempotency strategy, and reconciliation.

## 11. Why not check whether an event exists before inserting?
Two workers can both observe that it is absent and then insert concurrently. A database uniqueness constraint resolves the race atomically; application checks alone do not.

## 12. What makes event IDs stable?
A SHA-256 hash of the versioned event type, scenario/resource identity, normalized time, rule parameters, and CPU evidence. Replaying identical inputs produces the same ID. A genuinely new run should have a new scenario identity.

## 13. Does hashing make messages trustworthy?
No. Anyone who can change a message can compute a new hash. The hash supports content identity, not authentication. Production trust requires authenticated producers, restricted queue policies, and validation.

## 14. How do you validate queued input?
Pydantic checks types, rejects extra fields, enforces simulator-only source/type, requires timezone-aware timestamps and finite CPU percentages, checks evidence length/threshold conditions, and verifies ID consistency. Malformed input never reaches the insert path.

## 15. What is the dead-letter queue for?
It separates repeatedly failing messages from normal work so they can be inspected and replayed deliberately. It is not a fix for the underlying fault. We tested invalid-message redrive in Moto after three receives.

## 16. Why PostgreSQL and JSONB?
We need transactions and relational workflow data. Queryable identity/time fields remain columns; JSONB holds versioned evidence. pgvector is a planned extension for RAG, not currently installed.

## 17. What do SQLAlchemy and psycopg each do?
SQLAlchemy builds SQL and manages engines/connections/transactions. Psycopg is the driver that communicates with PostgreSQL. We use PostgreSQL-specific conflict handling through SQLAlchemy.

## 18. Why Alembic instead of creating tables whenever the app starts?
Migrations are a versioned history of deliberate schema changes. They separate deployment changes from request handling, and let us review which schema revision exists. Downgrading a migration can destroy data, so it is not routine cleanup.

## 19. How is database access restricted?
The API gets its own login and secret, SELECT on the event table, and no table-write/schema-create privileges. It defaults to read-only transactions and checks its principal/permissions at startup. Integration tests verify actual PostgreSQL write denial, beyond mocked behavior.

## 20. Why isn't a read-only transaction setting sufficient?
A user can sometimes change the transaction mode. We grant no event-table write privileges, so disabling transaction read-only mode still cannot delete rows. We tested that with a zero-row DELETE and asserted permission-denied SQLSTATE 42501.

## 21. How do API validation and errors work?
Invalid limits, offsets, sources, or IDs return 422. A valid but missing ID returns 404. Dependency failures return a sanitized 503. Successful empty lists return 200. A generated request ID links response headers to structured logs.

## 22. Why separate liveness from readiness?
The process may be alive while the database is unavailable. Liveness should not require a healthy dependency; readiness checks whether requests depending on the event table can currently be served.

## 23. Why use ordinary def endpoints rather than async def for SQL queries?
The current database driver path is synchronous. FastAPI runs synchronous handlers in a thread pool. Calling blocking database work directly inside an async handler would block the event loop. Async SQLAlchemy can be evaluated when concurrency requirements justify it.

## 24. How do you paginate?
The API caps page size at 100 and offsets at 10,000, sorts by receipt time with an event-ID tie-breaker, and fetches one extra row to calculate has_more without a full count. Offset pages can shift while inserts happen; cursor pagination is a future improvement.

## 25. How are credentials handled?
Local secrets live in ignored files and are passed at container runtime, not baked into images. The API receives only its own database secret. AWS development login uses browser-issued temporary credentials; long-lived root access keys are inactive. Cloud secret management is not yet implemented.

## 26. What is the difference between an image and container?
An image packages program files and dependencies. A container is an instance with its own process/filesystem state. Removing a container with --rm does not remove the reusable image; a named volume can retain database data across container replacement.

## 27. What is mocked and what is real in your tests?
Unit tests mock the database repository or queue client to isolate behavior. Integration tests exercise actual local PostgreSQL permissions and the Moto server. Live HTTP checks exercise the running API and stored events. None proves real AWS IAM or availability.

## 28. What are your main current limitations?
Simulation-only telemetry, volatile emulator queues, batch detector state, one-batch workers, no real EventBridge/SQS validation, no production user-login/identity provider or rate limiting, no frontend, and no AI investigation or remediation. Development JWT viewer checks exist. Local import tools still use the database administrator; separate runtime writer roles remain to implement.

## 29. What would change before public deployment?
Production identity-provider integration and full workflow roles beyond the local viewer gate, restricted runtime writer permissions, managed secrets, TLS and network policy, rate limiting, durable cloud queues, operational monitoring, cloud integration tests, deployment/rollback procedures, and cost controls. The current API is bound to localhost and must not be published as-is.

## 30. What results can you honestly put on a resume today?
You can describe an implemented local incident-event pipeline with validated inputs, idempotent PostgreSQL persistence, queue retry/DLQ checks, and a JWT-gated read-only API. Do not claim a production login provider, autonomous AWS deployment, measured MTTR improvement, RCA accuracy, or Bedrock integration until those exist and are measured.

## 31. Is a JWT encrypted?
No. Our JWT is signed, and its claims are readable. Never put secrets in the payload. Signature verification checks that claims were signed using the trusted key and have not changed without re-signing.

## 32. How do you validate access tokens?
The server fixes the allowed algorithm to HS256, verifies the signing key, requires issuer/audience/subject/role/time claims, checks expected issuer and audience, enforces expiry/not-before, and validates strict claim types and a bounded 15-minute lifetime.

## 33. What is the difference between 401 and 403 here?
401 means credentials are missing, invalid, or expired. 403 means the token is valid but its role has no events:read permission. Both decisions occur before accessing event data.

## 34. Does the local issuer verify a user's real identity?
No. The developer running the local CLI already controls the signing key and chooses a development subject label. Production needs a real identity provider and verified users. Our CLI is a testing issuer, not a password-login or OIDC service.

## 35. How do you revoke a JWT?
This slice has no per-token revocation list. Tokens expire in 15 minutes; rotating the signing key and restarting invalidates all old tokens. Immediate individual revocation and production key rotation require additional design.

## 36. Does a viewer JWT grant AWS or database privileges?
No. It permits an HTTP event-read operation under the app's role policy. The API independently uses a SELECT-only PostgreSQL account. AWS IAM identity, database identity, and token subject are separate authorization boundaries.

## 37. Why build a fake model provider first?
It lets us verify request/output contracts and failure handling without inference charges or model variability. The current fake is deterministic Python. Real Bedrock integration has not been implemented.

## 38. What if a provider returns malformed output?
We validate the JSON schema, output size, and supplied event citation. There is at most one repair attempt. Continued failure returns an explicitly marked deterministic fallback, with sanitized error codes.

## 39. Does structured output guarantee factual accuracy?
No. It checks structure and allowed references, not truth in prose. The current root-cause field must be null because CPU evidence alone cannot establish cause. Real-model grounding and adversarial evaluation remain future work.

## 40. Does the investigation demo change anything?
The analysis CLI reads a saved event with the restricted database login and prints a report. It does not store a finding, execute suggested checks, or remediate infrastructure. Its Compose dependencies can run the existing migration/reader setup first.

## 41. What does the investigator add beyond a provider call?
It validates the event, inventories evidence and collector gaps, invokes the bounded summarization step, and returns an explicit outcome plus ordered execution trace. It currently follows a fixed workflow with a fake provider, not model-directed tool selection.

## 42. Why distinguish unavailable evidence from an empty result?
An unconnected log collector tells us nothing about whether errors occurred. A successful search with no results is a different observation. We explicitly mark sources that are not connected and do not pretend to have searched them.

## 43. Why do event ID and run ID differ?
Event identity is stable for replayed source evidence. A run ID identifies one investigation invocation. Running the same event twice gives two run IDs and two saved snapshots. Reusing an existing run ID fails the primary-key constraint instead of overwriting history.

## 44. Is the execution trace an audit log or model reasoning?
It records observable workflow steps and outcomes, including fallback, without private model reasoning. Completed traces are now saved inside append-only report snapshots with role-based database access. This is not cryptographically tamper-evident history; an administrator can still modify it.

## 45. Why separate the investigator's database role from the API's?
The investigator needs SELECT on source events and INSERT on investigation history. The API only needs SELECT. Separate credentials and grants keep an API compromise from inheriting the report writer's privileges. The investigator cannot edit or delete saved reports.

## 46. Why use a foreign key for saved runs?
Every report refers to a saved source event. PostgreSQL enforces that reference at insertion and prevents deleting a referenced source event without handling its history. It does not prove the nested JSON report is factually accurate.

## 47. Does a successful investigation imply successful persistence?
No. The CLI saves the generated report in a transaction and prints persisted true only after commit. A save failure exits without claiming persistence. If a response is lost after commit, inspect history before rerunning; durable job retries are not implemented.

## 48. Are stored report snapshots a resumable workflow engine?
No. Only completed reports are appended. There are no saved intermediate checkpoints, worker leases, durable job IDs, or crash-resume semantics. Those require additional workflow design.

## 49. Are the new request-rate and log records real telemetry?
No. An explicit traffic-surge-v1 option generates scripted fixtures relative to a saved simulation event. Each record is labeled simulated with a fixture source. The default workflow still marks unconnected sources unavailable.

## 50. How do you keep unrelated evidence out of an investigation?
Validate its event ID, resource ID, supported kind/source, and timezone-aware timestamp within a five-minute pre-alert window. Reject duplicate kinds, oversized sets, and content/ID mismatches before calling the provider. This local scope rule is not a universal production investigation window.

## 51. Does an evidence hash prove its source is trustworthy?
No. It is a deterministic content identity and detects content changes against that identity. An author can fabricate content and recompute its hash. Source authentication, collection permissions, and trustworthy ingestion are separate concerns.

## 52. Why leave root cause null after adding deployment and traffic context?
The data is scripted and demonstrates correlation, not causation. A deployment preceding a symptom or increased request rate does not eliminate alternative explanations. Real diagnosis requires additional observations and evaluation; the fake provider deliberately does not claim causal certainty.

## 53. Is local runbook lookup the same as completed RAG?
No. We retrieve project-authored guides by structured tag overlap and attach their excerpts to reports. Retrieved text is not passed into the fake provider, and there is no real generation, embedding index, or semantic search. It is a knowledge-retrieval foundation.

## 54. What does the runbook relevance score mean?
The number of matching structured tags. It helps rank a tiny curated library and is not diagnostic confidence or evidence that a runbook's hypothesis is correct. Ties use stable runbook IDs, and results are bounded.

## 55. How can you tell what guidance an older report showed?
Each saved match includes its source path, full-file content hash, actual excerpt, and truncation flag. A later library change affects new runs after rebuilding the image; saved snapshots retain their original excerpts and revisions.

## 56. What happens if the runbook library is unavailable?
The report records unavailable with a generic code and no partial matches, then continues the evidence summary. This is distinct from provider fallback. Retrieving a runbook never executes its instructions or authorizes remediation.

## 57. How does the frontend get its data?
Browser-native JavaScript calls same-origin read endpoints through a loopback Python bridge. The bridge forwards the private development viewer token to the existing FastAPI API. The API still authenticates requests and reads with its SELECT-only database role. Browser storage contains a pane preference, not the token.

## 58. Is filtering global, and is the interface realtime?
No. Filtering applies to the loaded 25-event page, and each displayed event loads at most its latest 100 runs. Refresh fetches a new snapshot. The interface labels these limits and does not fabricate live agent streams or global search results.

## 59. What happens when the API stops responding after a successful load?
The screen retains the last visible records and marks the snapshot stale. A session error clears records and asks for local viewer renewal. An event with no saved run is different from history that failed to load.

## 60. How did you validate frontend quality beyond appearance?
I recorded five specific initial design problems and fixed them, then checked alignment, rendered text contrast, focus/control states, keyboard flows, clipboard, resizing, and four responsive widths. Browser tests exercise loading, empty, expired-session, unavailable, and stale states. This is evidence of the first screen's behavior, not a claim of full production accessibility or live AWS readiness.

## 61. Why add a separate investigation-history view?
An incident event and an investigation invocation have different identities and timestamps. One event can have several report snapshots with different workflow versions, evidence, and guidance. The inbox is event-focused; history is run-focused and never silently replaces an old snapshot with the newest run.

## 62. How do you prevent late network responses from showing the wrong report?
List/detail requests use sequence counters. Selecting a different run or refreshing invalidates older detail work. A late response is ignored instead of replacing the active report or source event. Browser tests deliberately delay one run response and then select another.

## 63. What does workflow elapsed time measure?
The recorded workflow finished_at minus started_at interval. It preserves sub-millisecond precision from Python's timestamps. It excludes later database persistence/network work and is not model latency, customer impact, or recovery time. Missing or invalid intervals remain Not recorded.

## 64. What if a saved run's original event cannot be fetched?
The report snapshot remains readable, with an explicit missing/unavailable source message. The interface does not show invented zero CPU values or borrow another source event. Trace and saved runbook guidance remain scoped to that same selected report.

## 65. Is Bedrock connected to the running investigator?
No. A Converse transport adapter passes offline SDK contract tests, but the current workflow deliberately blocks real providers and continues using fake-v2. Live activation requires sandbox/cost review and honest attempt-level usage/model-call accounting.

## 66. Why inject the Bedrock client?
It keeps credential discovery and environment configuration outside business logic. Tests use a real SDK client with dummy credentials and Stubber; they also pass with container networking disabled. Production clients will require explicit temporary identity, bounded timeouts, and bounded retries.

## 67. Why check stopReason as well as parsing JSON?
A response may stop because of token exhaustion, filtering, or a tool request. The adapter only accepts completed assistant text with end_turn. Output still needs schema, citation, and semantic checks; completed text alone does not establish root cause.

## 68. Do token counts prove cost control?
No. Successful adapter replies expose returned input/output counts. The application now aggregates known response counts across attempts and marks missing usage explicitly. Live model attribution, model-specific pricing, and budget/activation controls remain outstanding; paid inference is disabled under the free-only policy. Output token limits are not a hard spending cap.

## 69. Why keep per-attempt token usage if a repair succeeds?
The first response may still have consumed tokens even when it failed JSON or citation validation. The ledger retains all attempts, including attempts before deterministic fallback. Complete totals require known counts for every attempt; missing telemetry produces partial or unknown totals, with separate known subtotals.

## 70. Does free-only mean the project cannot progress?
No. We can build and evaluate the pipeline locally with Docker, PostgreSQL, Moto, scripted evidence, fake providers, and offline Bedrock SDK contracts. These demonstrate engineering behavior; they do not measure real-model quality or prove a live AWS deployment.
