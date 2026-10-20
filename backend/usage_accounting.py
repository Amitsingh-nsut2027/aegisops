"""Aggregate reported token usage without treating missing telemetry as zero."""
from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from llm_provider import ProviderReply


def attempt_usage(attempt: int, outcome: Literal["accepted", "invalid_output", "provider_failure"],
                  reply: ProviderReply | None) -> dict:
    def count(value):
        return value if type(value) is int and value >= 0 else None

    return {"attempt": attempt, "outcome": outcome,
            "input_tokens": count(reply.input_tokens) if reply else None,
            "output_tokens": count(reply.output_tokens) if reply else None}


def aggregate_usage(attempts: list[dict]) -> dict:
    totals = {}
    known = {}
    for key in ("input_tokens", "output_tokens"):
        values = [item[key] for item in attempts]
        known[key] = sum(value for value in values if value is not None)
        totals[key] = known[key] if values and all(value is not None for value in values) else None
    reported = sum(item[key] is not None for item in attempts for key in totals)
    status = ("not_reported" if reported == 0 else
              "complete" if reported == len(attempts) * 2 else "partial")
    return {**totals, "known_input_tokens": known["input_tokens"],
            "known_output_tokens": known["output_tokens"], "status": status,
            "source": "provider_response", "is_cost_estimate": False}
