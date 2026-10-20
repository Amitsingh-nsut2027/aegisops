# Phase 6 — first read-only investigator workflow

## Purpose and current scope
An investigator must show which evidence it used, which evidence is missing, and what happened during the run. We now wrap the Phase 5 provider in a fixed local workflow. This is the first investigator foundation, using saved simulation events and a deterministic fake provider. It is not yet an LLM-controlled agent, live AWS investigation, or the completed Phase 6 ambition. The subsequent [history slice](investigation-history.md) adds report persistence; current behavior is reflected below.

## Run it
From the project root:
```sh
docker compose build investigator
docker compose run --rm investigator
```

Without an ID it chooses the latest received simulation event, ordered by database receipt time and then event ID. To investigate a particular event, replace the placeholder below with its 64-character event ID:
```sh
docker compose run --rm investigator python investigator_cli.py --event-id YOUR_EVENT_ID
```

A missing ID produces an error; it never silently investigates another event. Malformed IDs are rejected before database access. The CLI checks its reader role, validates the payload and event hash, and checks that the row's ID matches its payload.

## Workflow steps
The current workflow v3 also retrieves local runbook excerpts between inventory and summarization, adding a fifth trace step. See [local runbooks](local-runbooks.md). This guidance is attached separately from the provider's evidence summary and is not executed.

The default path below remains CPU-only. The later [supplemental evidence slice](simulated-evidence.md) adds an explicit opt-in scripted scenario, validated event/resource/time scope, and provider citations. It never silently connects real data sources.

1. **Validate event:** verify the structured simulation event and CPU evidence. Invalid input stops the workflow before a provider call.
2. **Inventory evidence:** attach the saved CPU readings. Mark request rate, deployment history, and application logs as unavailable because no collectors are connected. No external lookup is attempted.
3. **Summarize evidence:** use the Phase 5 provider contract, output validation, bounded repair, and deterministic fallback. Only the saved event is sent to the fake provider; the inventory does not pretend to supply additional telemetry.
4. **Finish:** return `state: needs_evidence`. The workflow ran to completion, but the investigation remains unresolved because there is insufficient causal evidence.

## Report fields
| Field | Meaning |
|---|---|
| run_id | New identity for this invocation; replaying an event creates another run ID |
| workflow_version | Version of the fixed workflow |
| event_id | Stable identity of the source event |
| state | needs_evidence; this does not mean incident resolution |
| observed_at | Synthetic time from the simulation event |
| started_at / finished_at | Actual UTC execution timestamps |
| evidence_checks | Available evidence and explicit collector gaps |
| analysis | Provider identity, simulation flag, validation/fallback outcome, and summary |
| trace | Ordered observable steps and outcomes |

The trace records operational facts, not hidden model reasoning. Each entry has a sequence, step, status, UTC timestamp, and short detail. A provider fallback is visible in both the trace and analysis. Root cause remains null.

## State and access boundaries
Workflow state is in memory while running. On completion, the CLI appends a report snapshot to PostgreSQL and prints it after commit. Saved reports are readable through authenticated /investigations routes. A process failure before saving loses that invocation's trace. This is durable report history, not a resumable job or incident lifecycle state machine.

The CLI now uses the dedicated aegis_investigator PostgreSQL role: SELECT on source events and SELECT/INSERT on history, with no UPDATE/DELETE grants. The API retains its separate SELECT-only role. No HTTP token is needed for this local developer command; database authentication is a separate boundary. The service receives its investigator password, without the JWT signing key or AWS credentials. Compose may run the migration/role setup dependency before starting it.

Suggested checks are descriptions, not tool execution. There are no log, metrics, or deployment collectors, external actions, remediation, or model-directed tool selection in this step. No AWS or model charges are incurred by the fake workflow.

## Decisions and alternatives
A fixed workflow is easy to inspect, bound, and test before allowing model-directed decisions. Missing evidence is explicitly unavailable rather than an empty result: an unconnected log source is different from searching logs and finding no errors. Unique run IDs distinguish separate executions from a stable event identity; they do not provide database deduplication because run storage does not exist yet.

The existing provider schema validates structure and citations, not all factual claims in prose. Fake output is deterministic. Real-model evaluation, runtime tool policies, restricted collectors, resumable workflow state, and production observability remain future work.

## Verification
Seven new workflow tests cover evidence gaps/trace, replay identity, visible fallback, rejected invalid events, selected/latest event reads, missing IDs without substitution, and row/payload identity mismatch. The complete unit suite has 44 passing tests. The Docker CLI was also exercised against a saved PostgreSQL event and returned needs_evidence with four trace steps and a null root cause.

## Interview explanation
“I built a bounded read-only investigator workflow over validated saved events. It inventories available evidence, explicitly identifies missing collectors, and produces a structured summary with an observable execution trace. Provider failures use a bounded retry and marked fallback. Each run has its own identity, while source event identity remains stable. It currently uses deterministic simulated output, with no real model or AWS tool calls.”

## Next slice
Investigation history is now implemented; continue with [its notes](investigation-history.md) to understand persistence and authenticated API reads. Real Bedrock integration still depends on the outstanding sandbox and budget review. Frontend work must follow docs/UI-REQUIREMENTS.md and the design approval checkpoint.
