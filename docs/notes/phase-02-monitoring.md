# Phase 2 — Local CPU monitoring and incident events

Status: deterministic batch detector and structured simulator events verified. No live AWS monitoring or streaming state yet.

## Concepts and purpose
A metric is a numeric observation with a unit, timestamp, and resource context. An alert reports a condition needing investigation; it is not a root cause. Deterministic rules are sufficient for explicit CPU thresholds; adding an LLM here would add uncertainty without useful reasoning.

## Detector algorithm
backend/simulator.py exposes detect_cpu_alerts(samples, threshold=90, required_samples=3).
- For each CPU value strictly above the threshold, increment consecutive_high.
- At three consecutive high values, emit one alert and latch alert_active.
- More high values in the same episode do not emit repeat alerts.
- At or below the threshold, reset the streak and latch.
- Return one record per input sample. Keep JSON printing inside the main guard so importing the function does not run the demo.
- Reject invalid/non-finite/out-of-range values and non-positive/non-integer windows.

Counters are local to the function: separate calls start fresh. This is a batch teaching detector, not a persistent production stream processor. Future telemetry adapters must address missing/out-of-order samples, resource-specific state, timestamps, and aggregation windows.

## Verified examples
| Samples | Alert sample numbers |
|---|---|
| 35, 42, 91, 45, 92, 95, 96, 40 | 7 |
| 91, 92, 93, 94, 95, 90, 91, 92, 93 | 3 and 9 |

The second sequence verifies duplicate suppression, exact-threshold reset, and rearming after recovery. An initial skeleton containing only pass produced no output; pass deliberately does nothing.

## Event generation
backend/incidents.py converts alerts into IncidentEvent dataclasses. Fields include event_id, event_type, source, scenario_id, resource_id, observed_at, sample, severity, threshold/window, and cpu_evidence.

The demo labels source=simulator and resource=simulated/ecs/api-service. It uses a fixed UTC start time and one-minute sample spacing for reproducibility. Times are synthetic. Warning severity is a demonstration symptom label, not a measure of verified service impact.

A SHA-256 hash of canonical replay inputs provides stable event IDs. Replaying the same scenario yields the same IDs; new simulation runs need distinct scenario IDs. Hashes do not authenticate producers. Event IDs alone do not prevent duplicates: the persistence slice adds a primary-key constraint.

## Files and flow
CPU samples → simulator.py detector → incidents.py event builder → JSON lines. Event dataclasses are a local representation; the later queue boundary adds Pydantic validation before untrusted messages reach storage.

## Commands
```sh
docker run --rm -v "$PWD/backend:/app:ro" -w /app python:3.12-slim python simulator.py
docker run --rm -v "$PWD/backend:/app:ro" -w /app python:3.12-slim python incidents.py
```

The bind mount makes backend files readable inside /app without copying them into this temporary container; :ro prevents writing through the mount. The installed project image is used by later Compose services.

## Verification
Learner Docker runs confirmed baseline and edge-case detector output plus two structured events at samples 3 and 9. Six monitoring unit tests cover detector behavior, evidence/time, replay identity, normal/empty inputs, invalid settings/values, and fresh state/custom windows. Import behavior was checked separately before the reusable refactor was accepted.

## Common mistakes and interview takeaways
- Count consecutive breaches, not all breaches in the batch.
- Distinguish greater-than from greater-than-or-equal.
- Reset the episode so a new failure can alert again.
- Separate calculation from printing to make behavior reusable and testable.
- Explain why one symptom does not establish causation.
- Three samples are not automatically three minutes; actual duration depends on timestamps.

## AWS/cost/security scope
No AWS services, credentials, or cloud charges involved. Inputs are deterministic local fixtures. Real CloudWatch integration and the ten-scenario evaluation harness are future work. Read local-persistence.md next, then phase-03-event-queue.md.
