# Phase 5 — investigation provider foundation

## What this step does
Current extension: [supplemental evidence](simulated-evidence.md) adds a v2 context envelope containing event and supplemental_evidence. The current provider is fake-v2; summaries may cite the event plus supplied fixture IDs, while root cause stays null. The CPU-only command below remains supported.

The local CLI reads one saved simulation event through the SELECT-only database role, validates its payload, and sends it through a provider interface. The only implemented provider is `FakeProvider`: deterministic Python, with no model inference, AWS request, or model charge. This is the integration foundation, not completed Bedrock integration or an autonomous agent.

## Why an interface?
`LLMProvider` is a Python Protocol: it describes the name, simulation flag, and generate method that providers must expose. The investigation code depends on that contract rather than an AWS SDK response. A future Bedrock adapter can translate between the common request/reply and a particular model's API. That adapter still needs implementation, testing, credentials, cost controls, and cloud review. The simulation flag is a development guard, not a security sandbox for arbitrary Python plugins.

## Follow the data
1. `llm_demo.py` checks the dedicated reader role and selects one saved event, ordered by receipt time and ID.
2. `QueuedIncident` validates its schema, evidence window, and replay identity.
3. `investigate` serializes the evidence and checks a 16,000-byte context limit. This is a byte limit, not a model token estimate.
4. `ProviderRequest` carries instructions, evidence, an output JSON schema, and a 512-token requested output allowance. A future real adapter must enforce that allowance through its model API; the fake provider does no token generation.
5. Output is limited to 64,000 UTF-8 bytes and validated with Pydantic. Only the supplied event ID may be cited. The current schema requires insufficient evidence and a null root cause. Follow-up checks are restricted to request rates, deployments, and logs.
6. Invalid output or an expected provider failure gets one repair attempt, for at most two calls. Failure after that returns a deterministic summary. Oversized input skips the provider and falls back immediately.
7. The CLI prints a report. It does not persist a finding, add an API route, execute checks, or change infrastructure.

## What validation can and cannot prove
JSON validation checks structure, types, and allowed references. It does not prove that arbitrary prose is true. The root-cause field cannot claim a cause in this lesson, but a future real model could still put unsupported assertions in its summary. Evidence grounding and adversarial evaluation remain required before real model output is trusted. Prompt instructions about untrusted evidence are helpful guidance, not a complete prompt-injection defense.

High CPU establishes a symptom. To investigate cause, we would need additional evidence such as workload changes, deployment history, logs, profiling, or saturation metrics. The fake provider explicitly leaves root cause undetermined. Suggested next checks are descriptions only, with no tool execution.

## Run from the project root
```sh
docker compose build analysis
docker compose run --rm analysis
```

The service starts the database/setup dependencies if needed and receives only its reader password. It receives no JWT signing key or AWS credentials. Existing migrations/reader-role setup may run before the CLI; the analysis itself only reads data.

Expected current report fields: provider `fake-v2`, simulated `true`, model_called `false`, attempts `1`, used_fallback `false`, and root_cause `null`. Token counts are null because no model usage was measured; they are not fabricated estimates. Saved observation times remain synthetic scenario times.

## Failure behavior and tests
Seven provider tests cover the fake output, successful repair, invalid citation/root-cause/action/extra fields, sanitized provider failures, context limit, output limit, and the real-provider guard. The full unit suite has 37 passing tests. The CLI also successfully read an existing PostgreSQL event and returned fake-v1, one attempt, no fallback, and null root cause. Expected provider exceptions produce generic error codes; programming errors are not silently converted into findings.

## Interview explanation
“I separated investigation orchestration from the model provider, using a deterministic fake to test the contract locally. Outputs must match a typed schema and cite the supplied event. Repair attempts are bounded, and failures return an explicit deterministic fallback. CPU evidence alone leaves root cause undetermined. Real Bedrock integration and semantic grounding evaluation are still future work.”

## Next
Build a first read-only investigator workflow with explicit evidence and workflow state. Keep fake-provider reports labeled as simulation. Real Bedrock calls remain pending sandbox/budget review. Frontend implementation still requires the agreed design review and quality standards.
