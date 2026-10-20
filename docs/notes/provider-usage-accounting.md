# Provider usage accounting — local-only

## Concept
One investigation can ask a provider twice: an initial response, then one repair if validation fails. Looking only at the successful response would discard usage from the first attempt. An exception may also hide usage; absence of telemetry must not become zero.

```text
validated event → provider attempt 1 → validate JSON/citations → accepted
                                      ↓ invalid
                 provider attempt 2 → validate → accepted or deterministic fallback
                    ↓ per-attempt usage ledger
                 known subtotals + complete / partial / not_reported status
```

## Implementation and decisions
backend/usage_accounting.py records each attempt's number, accepted/invalid_output/provider_failure outcome, and optional input/output counts. Only non-negative integers are accepted as counts; booleans and invalid values become unknown. There is no raw model output, credential, or exception message in the ledger.

backend/llm_provider.py records usage in finally so an accepted response's break still records its attempt. Counts from JSON/citation failures remain recorded. A transport error has unknown counts. aggregate_usage returns a total for a token dimension only when every attempt reported that dimension. known_input_tokens and known_output_tokens sum available counts even when full totals are unknown. They are subtotals, not zero-filled totals. The status is complete, partial, or not_reported. These are provider-reported token counts, not verified monetary costs.

FakeProvider continues returning null counts and model_called=false. Artificial counts in tests belong to explicitly scripted providers. The real-provider gate remains enabled. Returned usage from a Bedrock response rejected inside the adapter is currently unknown to the workflow, not silently counted as zero. End-to-end live accounting, pricing, and live-model attribution remain deferred under the [free-only policy](../COST-POLICY.md).

The Docker image includes the helper. New reports append the ledger inside analysis; old snapshots are not rewritten. Existing payload readers tolerate absent ledger fields in older runs.

## Verified
- All 83 backend unit tests passed with Docker networking disabled: the previous 75 plus eight accounting tests.
- Tests cover two-attempt totals, fallback retention, transport failure/partial usage, fake-provider unknown counts, no-call context rejection, zero versus unknown, malformed counts, and independent input/output completeness.
- Rebuilt the local investigator image and saved one traffic-surge-v1 report with model_called=false, usage status not_reported, and one accepted attempt with null counts. Its run ID is bd5967211b054b11bacb85387c88fef7.
- No AWS model calls or resource creation occurred. Read-only AWS account checks and their permission limits are recorded in COST-POLICY.md.

```sh
docker run --rm --network none -v "$PWD/backend:/app:ro" -v "$PWD/tests:/tests:ro" aegisops-backend:local python -B -m unittest discover -s /tests
docker compose run --rm --no-deps investigator python investigator_cli.py --evidence-scenario traffic-surge-v1
```

The second command deliberately appends a new simulated report each time. The first command changes no database data.

## Interview takeaways
A failed response may still consume model tokens. Retry usage belongs to the investigation's total. Unknown usage is not free usage. Cost estimates need model pricing and complete telemetry, and are distinct from provider call counts or simulation status. A fake-provider evaluation verifies plumbing and deterministic behavior, not real LLM accuracy.
