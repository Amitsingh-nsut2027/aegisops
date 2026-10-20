"""Converse transport adapter. No client creation or live CLI wiring in this slice."""
import json
from typing import Protocol

from botocore.exceptions import BotoCoreError, ClientError

from llm_provider import MAX_CONTEXT_BYTES, ProviderError, ProviderReply, ProviderRequest


class ConverseClient(Protocol):
    def converse(self, **kwargs) -> dict: ...


class BedrockProvider:
    name = "bedrock-converse-v1"
    simulated = False

    def __init__(self, client: ConverseClient, *, model_id: str):
        # Caller must supply a client: importing this module never discovers credentials.
        if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 2048:
            raise ValueError("An explicit model ID is required")
        if model_id != model_id.strip() or any(char.isspace() for char in model_id):
            raise ValueError("Invalid model ID")
        self.client = client
        self.model_id = model_id

    def generate(self, request: ProviderRequest) -> ProviderReply:
        if (type(request.max_output_tokens) is not int or
                not 1 <= request.max_output_tokens <= 512):
            raise ProviderError("Invalid output token limit")
        if len(request.context_json.encode("utf-8")) > MAX_CONTEXT_BYTES:
            raise ProviderError("Context limit exceeded")
        # Keep trusted schema/repair guidance out of the untrusted evidence message.
        system = request.system_prompt + "\nOutput JSON schema:\n" + json.dumps(request.output_schema)
        if request.repair_feedback:
            system += "\nRepair requirement:\n" + request.repair_feedback
        if len(system.encode("utf-8")) > MAX_CONTEXT_BYTES:
            raise ProviderError("Instruction limit exceeded")
        try:
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": request.context_json}]}],
                inferenceConfig={"maxTokens": request.max_output_tokens},
            )
        except (BotoCoreError, ClientError):
            raise ProviderError("Bedrock request failed") from None
        return self._reply(response, request.max_output_tokens)

    @staticmethod
    def _reply(response: dict, max_tokens: int) -> ProviderReply:
        try:
            # Reject truncation, guardrail stops and tool calls rather than accepting partial text.
            if response["stopReason"] != "end_turn":
                raise ValueError("Incomplete response")
            message = response["output"]["message"]
            blocks = message["content"]
            if message["role"] != "assistant" or not isinstance(blocks, list) or not blocks:
                raise ValueError("Missing assistant response")
            if any(not isinstance(block, dict) or set(block) != {"text"} or
                   not isinstance(block["text"], str) for block in blocks):
                raise ValueError("Unexpected content block")
            text = "".join(block["text"] for block in blocks)
            if not text.strip() or len(text.encode("utf-8")) > 64000:
                raise ValueError("Invalid response length")
            usage = response["usage"]
            counts = [usage["inputTokens"], usage["outputTokens"]]
            if any(type(value) is not int or value < 0 for value in counts) or counts[1] > max_tokens:
                raise ValueError("Invalid usage")
            return ProviderReply(text, input_tokens=counts[0], output_tokens=counts[1])
        except (KeyError, TypeError, ValueError):
            raise ProviderError("Invalid Bedrock response") from None
