# Phase 5 — Bedrock transport adapter, offline checkpoint

## Concept and purpose
A provider adapter translates the application's request/response types into a vendor API. The investigator should not depend on Bedrock message formatting. Bedrock Converse uses messages, a separate system instruction, inference parameters, response content, stop reason, and token usage. See the [official Converse reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html).

```text
Current application: event → investigate → FakeProvider → validated report
Future connection:  ProviderRequest → BedrockProvider → injected Converse client
                                                    ↓
                   ProviderReply ← text + token counts + completed response
Offline verification: real SDK client → Stubber (no network) → response fixture
```

This slice implements and tests the transport boundary. It does not connect Bedrock to the running investigator. The existing real-provider gate still rejects this adapter before generate is called. The UI and saved reports continue using fake-v2.

## Files and behavior
- backend/bedrock_provider.py: requires an explicit client and model ID. Import/construction does not create clients, discover credentials, or access AWS. generate performs one converse method call; SDK retries/timeouts belong to the supplied client and must be bounded when live wiring is added.
- backend/llm_provider.py: ProviderReply now supports optional input_tokens/output_tokens. Existing fake replies remain compatible.
- backend/Dockerfile: includes the new module for future builds.
- tests/test_bedrock_provider.py: nine tests including SDK request/response contract validation with botocore Stubber.

The adapter sends trusted schema and repair feedback in system text. Untrusted evidence stays unchanged in the user message. The schema is an instruction in this slice, not server-enforced structured output. Existing Pydantic/citation validation will remain necessary when the real provider is enabled; schema validity cannot establish factual truth or eliminate prompt injection.

Input bounds: context and composed system instructions each at most 16,000 UTF-8 bytes; output request 1–512 tokens. Response text is limited to 64,000 bytes. Only assistant text blocks with end_turn are accepted. Truncation, tool requests, guardrail stops, malformed envelopes, and invalid usage counts fail with sanitized ProviderError messages. AWS exception text is not copied into reports.

## Decisions and alternatives
Client injection makes the adapter testable without a user's AWS identity. No model is chosen automatically: supported models/regions, capabilities, pricing, identity, and sandbox eligibility still require review. We use maxTokens without assuming every model accepts the same sampling parameters. No tools are configured and no returned tool request is executed.

Token counts are returned from a successful transport response. This is not yet end-to-end usage/cost accounting: local aggregation over repair attempts and explicit unknown telemetry are now implemented in [usage accounting](provider-usage-accounting.md). Live model attribution, pricing, and activation remain deferred under the free-only policy. Do not remove the real-provider gate on its own.

## Verification and commands
All 75 backend unit tests passed, including the nine new adapter tests. The nine adapter tests also passed in a container with networking disabled:

```sh
docker run --rm --network none -v "$PWD/backend:/app:ro" -v "$PWD/tests:/tests:ro" aegisops-backend:local python -B -m unittest discover -s /tests -p test_bedrock_provider.py -v
```

This uses the existing local backend image's dependencies and mounts current source read-only. On a fresh machine, build the image first. Fixtures use explicit dummy credentials; Stubber validates AWS SDK shapes and returns responses without contacting AWS. An initial test fixture used a fractional latencyMs; SDK validation rejected it, and it was corrected to an integer.

No resources were provisioned, no real model was called, and no findings were inserted. These tests cannot verify actual model access, regional availability, live latency/cost, response quality, or service-side permissions.

## Common mistakes and interview takeaways
- An HTTP 200 can contain a max_tokens stop; do not accept an incomplete answer as a successful investigation.
- SDK-shaped tests catch transport errors that an unrestricted Mock can miss.
- A model adapter passing offline tests does not mean the application is AI-powered yet.
- Token limits bound output volume; they are not a hard monetary cap.
- Credential discovery is kept outside the adapter. Future live calls must use authorized temporary identity and bounded SDK retries/timeouts.

## Next checkpoint
Before any live call: verify sandbox and budget constraints, select a supported model/region with a cost estimate, define explicit activation, and integrate attempt-level usage/model-call accounting with existing validation/fallback. Existing Phase 1 cloud prerequisites remain unresolved. No UI screen is added in this slice.

Update: the user requested free-only after this checkpoint. Follow [COST-POLICY.md](../COST-POLICY.md); do not proceed to live activation as the next step.
