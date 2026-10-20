import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from event_schema import QueuedIncident
from incidents import build_incident_events
from llm_provider import ProviderError, ProviderReply, deterministic_summary, investigate
from usage_accounting import aggregate_usage, attempt_usage


class UsageTests(unittest.TestCase):
    def setUp(self):
        raw = build_incident_events([91, 92, 93], "usage-test", "simulated/api",
                                    datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
        self.event = QueuedIncident.model_validate_json(json.dumps(asdict(raw)))
        self.valid = deterministic_summary(self.event).model_dump_json()
        self.provider = Mock()
        self.provider.name = "scripted-usage-test"
        self.provider.simulated = True

    def test_repair_counts_both_responses_not_just_the_accepted_one(self):
        self.provider.generate.side_effect = [ProviderReply("bad JSON", 117, 19),
                                               ProviderReply(self.valid, 128, 103)]
        report = investigate(self.event, self.provider)
        self.assertEqual(report["usage"]["input_tokens"], 245)
        self.assertEqual(report["usage"]["output_tokens"], 122)
        self.assertEqual(report["usage"]["status"], "complete")
        self.assertEqual([item["outcome"] for item in report["attempt_usage"]],
                         ["invalid_output", "accepted"])
        self.assertFalse(report["model_called"])

    def test_transport_failure_preserves_unknown_totals_and_known_subtotals(self):
        self.provider.generate.side_effect = [ProviderReply("bad JSON", 117, 19),
                                               ProviderError("private transport failure")]
        report = investigate(self.event, self.provider)
        self.assertTrue(report["used_fallback"])
        self.assertIsNone(report["usage"]["input_tokens"])
        self.assertIsNone(report["usage"]["output_tokens"])
        self.assertEqual(report["usage"]["known_input_tokens"], 117)
        self.assertEqual(report["usage"]["status"], "partial")
        self.assertEqual(report["attempt_usage"][1]["outcome"], "provider_failure")
        self.assertNotIn("private transport failure", json.dumps(report))

    def test_fallback_does_not_erase_usage_from_invalid_responses(self):
        self.provider.generate.side_effect = [ProviderReply("bad", 81, 14), ProviderReply("bad", 92, 17)]
        report = investigate(self.event, self.provider)
        self.assertTrue(report["used_fallback"])
        self.assertEqual(report["usage"]["input_tokens"], 173)
        self.assertEqual(report["usage"]["output_tokens"], 31)

    def test_fake_provider_has_no_invented_token_counts(self):
        report = investigate(self.event)
        self.assertIsNone(report["usage"]["input_tokens"])
        self.assertEqual(report["usage"]["status"], "not_reported")
        self.assertFalse(report["model_called"])
        self.assertEqual(len(report["attempt_usage"]), 1)

    def test_context_rejected_before_call_has_empty_ledger(self):
        with patch("llm_provider.MAX_CONTEXT_BYTES", 1):
            report = investigate(self.event, self.provider)
        self.provider.generate.assert_not_called()
        self.assertEqual(report["attempt_usage"], [])
        self.assertIsNone(report["usage"]["input_tokens"])

    def test_unknown_and_zero_are_distinct(self):
        zero = aggregate_usage([attempt_usage(1, "accepted", ProviderReply("{}", 0, 0))])
        self.assertEqual(zero["input_tokens"], 0)
        self.assertEqual(zero["status"], "complete")
        unknown = aggregate_usage([attempt_usage(1, "provider_failure", None)])
        self.assertIsNone(unknown["input_tokens"])
        self.assertEqual(unknown["status"], "not_reported")

    def test_invalid_usage_metadata_is_unknown_not_a_negative_or_boolean_count(self):
        usage = aggregate_usage([attempt_usage(1, "accepted", ProviderReply("{}", True, -8))])
        self.assertIsNone(usage["input_tokens"])
        self.assertIsNone(usage["output_tokens"])

    def test_input_and_output_completeness_are_independent(self):
        usage = aggregate_usage([attempt_usage(1, "accepted", ProviderReply("{}", 83, None))])
        self.assertEqual(usage["input_tokens"], 83)
        self.assertIsNone(usage["output_tokens"])
        self.assertEqual(usage["status"], "partial")
