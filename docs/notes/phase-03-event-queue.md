# Phase 3 — Local event-driven processing

Status: first local queue slice implemented and verified. Real AWS deployment, EventBridge routing, and production operational hardening remain pending.

## Concepts and purpose
- A producer sends an event; a worker receives and processes it independently.
- A queue buffers work so the worker does not have to be running when the event is published.
- Receiving temporarily hides a message (30 seconds here). It does not acknowledge success.
- Delete using the receipt handle only after the database transaction commits.
- A worker crash after commit but before acknowledgement can cause redelivery. The database primary key makes that replay idempotent.
- Invalid or repeatedly failing messages reach a dead-letter queue after three receives and another receive attempt triggers redrive in the emulator.
- Pydantic validates untrusted JSON before database access: field types, allowed source/type, timezone, finite percentage range, evidence window, and event-ID consistency.
- Event hashes establish deterministic identity, not cryptographic authentication; a sender can recompute a hash. The local source restrictions are not a replacement for production IAM and authenticated event producers.

## Flow
Simulator → producer → local SQS-compatible Moto queue → validating worker → PostgreSQL commit → queue acknowledgement.

## Components
- backend/queue_transport.py: local-only boto3 client, queue/DLQ setup, endpoint checks.
- backend/event_schema.py: strict queued-event contract and conversion to the existing event dataclass.
- backend/queue_worker.py: one receive batch, per-message persistence, acknowledgements, and failure summaries.
- backend/queue_demo.py: publish, work, and status commands.
- compose.yaml: Moto service (pinned image digest) and optional queue tooling profile. No Moto host port is published.
- tests/test_queue.py: acknowledgement ordering, failures, duplicates, validation, URL guard, empty polling.
- tests/integration/test_local_queue.py: uniquely named Moto test queues verify retry, acknowledgement, and DLQ behavior; only those test queues are removed.

## Local setup and commands
Run from the project root with Docker Desktop running and the existing ignored .env present:

```sh
docker compose build queue
docker compose run --rm ingest alembic upgrade head
docker compose run --rm queue python queue_demo.py publish --scenario-id queue-demo-v1
docker compose run --rm queue python queue_demo.py work
docker compose run --rm queue python queue_demo.py status
```

Dependencies start automatically. Publish creates the main queue and DLQ. A fresh scenario inserts two events; replaying the same scenario produces two duplicates and zero new rows. `work` processes one batch (up to ten messages), then exits; it is not a continuous worker service yet. A normal empty poll is not an error or proof that an AWS queue is permanently empty.

Stop the local queue/database with `docker compose --profile queue down`; this retains PostgreSQL's named volume but clears Moto's in-memory queue state. Republish the scenario after emulator restart. Do not remove the database volume to fix ordinary startup issues.

## Verification
- 13 unit tests passed in the Python container: six monitoring and seven queue tests.
- Three local Moto integration tests passed.
- queue-demo-v1 published two events; worker received/inserted/acknowledged two, with zero failures.
- Replay: received 2, inserted 0, duplicates 2, acknowledged 2, failed 0. SQL confirms exactly two rows for queue-demo-v1 and two for the earlier direct-import scenario. Queue and DLQ drained after verification.
- Dependency versions captured from the tested container and pinned; .in retains direct constraints.

## Cost and security
- No actual AWS SQS, EventBridge, IAM changes, or cloud charges for this lesson. Docker image/package downloads use the developer's network and local disk.
- boto3 uses explicit dummy credentials and a hardcoded local endpoint, independent of aegis-dev or root profiles. Returned queue URLs must point to http://moto:5000.
- Queue tools use the existing local database administrator for this exercise. Production must separate producer, consumer, migration, and database permissions.
- Logs summarize errors without printing raw untrusted message bodies or credentials.

## Limits and next work
Moto is a test emulator with volatile in-memory queue state; these tests do not prove real SQS durability, IAM, timing, ordering, or redrive behavior. Production SQS semantics require dedicated sandbox integration checks later.
No heartbeat/visibility extension, continuous worker, backlog metrics, EventBridge, or outbox yet. Database idempotency protects event inserts but does not implement exactly-once external actions. Other existing retail resources are unchanged.

## Interview takeaways
- Explain why acknowledging before commit can lose work.
- Explain why acknowledging after commit can duplicate delivery and how the database resolves it.
- Separate a malformed message (quarantine/DLQ) from temporary database unavailability (retry).

## References
- https://docs.getmoto.org/en/latest/docs/server_mode.html
- https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/client/receive_message.html
- https://docs.aws.amazon.com/boto3/latest/reference/services/sqs/client/delete_message.html
