# Supplemental evidence — explicit, scoped simulation

## Purpose
The investigator can now attach scripted request-rate, deployment, and application-log context to a saved CPU event. This exercises evidence scope, provenance, provider context, citations, and saved history before connecting real telemetry. These are generated fixtures, not AWS collectors or reconstructed historical facts.

## Run the richer demo
From the project root:
```sh
docker compose run --rm investigator python investigator_cli.py --evidence-scenario traffic-surge-v1
```

The existing optional --event-id argument can select a particular saved simulation event. Omitting --evidence-scenario preserves the CPU-only behavior: the three other sources remain unavailable. Nothing automatically enriches old reports.

In the enriched report, all four evidence_checks are available **within the simulation**. Each supplemental record explicitly has simulated true and source scripted-fixture/traffic-surge-v1. Root cause stays null and state remains needs_evidence. The report is appended to PostgreSQL and visible in authenticated GET /investigations without an API schema change.

## The scripted scenario
| Kind | Scripted content | Synthetic time relative to CPU alert |
|---|---|---|
| Request rate | Baseline 120 requests/second; recent 620 requests/second | One minute earlier |
| Deployment history | demo-api-v2 release | Four minutes earlier |
| Application logs | WARN: request queue length increased | One minute earlier |

The generator deliberately constructs this context relative to whichever simulation event you select. It does not claim that these observations actually happened. The rate comparison is fixed text, not a measured time series or computed baseline. The single WARN entry is not an exhaustive log search. A release preceding high CPU does not prove that release caused the symptom.

## Evidence contract and provenance
Each typed record contains evidence_id, event_id, resource_id, kind, source, simulated flag, observed_at, and bounded detail text. Identity is SHA-256 of canonical content. Timestamp representations such as Z and +00:00 are normalized to UTC before hashing. This detects changes relative to an expected hash, not malicious authorship: anyone able to construct a record can recompute its hash.

Before provider invocation, validation rejects:
- More than three supplemental records or duplicate kinds.
- Another event ID or resource ID.
- Naive timestamps, records after the alert, or records more than five minutes before it.
- Content that no longer matches its evidence ID, unsupported sources, extra fields, or oversized detail text.

The five-minute window is a local lesson policy, not a universal SRE rule. Real investigations may need longer and source-specific windows. Rejected evidence stops the run before any report is saved; it is not silently treated as good input. Collection failures/partial results from real connectors are not implemented.

## Provider changes
The v2 request context is an envelope containing event and supplemental_evidence. The context still has a 16,000-byte bound; output remains bounded and gets at most two attempts. FakeProvider is now fake-v2, prompt version cpu-investigation-v2, and workflow version cpu-investigator-v2. Older saved snapshots retain their original metadata.

The fake summary cites the source event and attached supplemental record IDs. Output validation requires the source event citation, rejects invented IDs and duplicates, and permits at most four citations. It does not require every attached record to be cited by arbitrary providers. The deterministic fallback uses the same validated input records. Raw evidence text is treated as data in prompt instructions; this is not a complete prompt-injection defense. A future real provider still needs semantic grounding evaluation.

The fake summary reports that extra context is attached; it does not infer a cause or execute follow-up checks. Even this richer dataset does not distinguish traffic load, code behavior, or other explanations with certainty. No actual model call, AWS request, or remediation occurs.

## Verification
Nine new tests cover deterministic fixtures and simulation labels, tampered contents, equivalent UTC serialization, event/resource isolation before provider execution, stale/future records, duplicate/oversized sets, complete report provenance and citations, provider context and invented citations, and unchanged default behavior. All 58 unit tests passed. Three writer integration tests also passed. A demonstration enriched report was appended to the local database; previous reports remain intact.

## Interview explanation
“I added opt-in simulated evidence with explicit provenance and bounded event/resource/time scope. Evidence is validated before entering the provider context, and output citations must refer to supplied IDs. The demo includes workload, deployment, and log context, but temporal correlation still does not establish root cause. Real telemetry connectors and model-based causal investigation are not implemented yet.”
