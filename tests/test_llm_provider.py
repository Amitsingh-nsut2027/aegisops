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
from llm_provider import FakeProvider, ProviderError, ProviderReply, deterministic_summary, investigate


class ProviderTests(unittest.TestCase):
    def setUp(self):
        raw = build_incident_events([91, 92, 93], "llm-test", "simulated/api",
                                    datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
        self.event = QueuedIncident.model_validate_json(json.dumps(asdict(raw)))
        self.valid = deterministic_summary(self.event).model_dump_json()
        self.provider = Mock(name="test_provider")
        self.provider.name = "test-fake"
        self.provider.simulated = True

    def test_fake_is_explicit_and_does_not_claim_root_cause(self):
        report = investigate(self.event, FakeProvider())
        self.assertEqual(report["provider"], "fake-v2")
        self.assertTrue(report["simulated"])
        self.assertFalse(report["model_called"])
        self.assertFalse(report["used_fallback"])
        self.assertIsNone(report["result"]["root_cause"])
        self.assertEqual(report["result"]["evidence_ids"], [self.event.event_id])
        self.assertIsNone(report["usage"]["input_tokens"])

    def test_repairs_once_then_accepts_valid_output(self):
        self.provider.generate.side_effect = [ProviderReply("not json"), ProviderReply(self.valid)]
        report = investigate(self.event, self.provider)
        self.assertEqual(report["attempts"], 2)
        self.assertFalse(report["used_fallback"])
        request = self.provider.generate.call_args.args[0]
        self.assertIsNotNone(request.repair_feedback)
        self.assertEqual(request.max_output_tokens, 512)

    def test_invalid_outputs_fall_back_with_bounded_attempts(self):
        for changes in [{"root_cause": "bad deployment"}, {"evidence_ids": ["invented"]},
                        {"next_checks": ["restart_service"]}, {"extra": "not allowed"}]:
            with self.subTest(changes=changes):
                self.provider.reset_mock()
                self.provider.generate.return_value = ProviderReply(json.dumps(
                    {**json.loads(self.valid), **changes}))
                report = investigate(self.event, self.provider)
                self.assertTrue(report["used_fallback"])
                self.assertEqual(self.provider.generate.call_count, 2)
                self.assertIsNone(report["result"]["root_cause"])

    def test_provider_failure_is_sanitized(self):
        self.provider.generate.side_effect = ProviderError("private credentials")
        report = investigate(self.event, self.provider)
        self.assertTrue(report["used_fallback"])
        self.assertEqual(report["errors"], ["provider_failure", "provider_failure"])
        self.assertNotIn("private credentials", json.dumps(report))

    def test_context_limit_prevents_provider_call(self):
        with patch("llm_provider.MAX_CONTEXT_BYTES", 1):
            report = investigate(self.event, self.provider)
        self.provider.generate.assert_not_called()
        self.assertEqual(report["attempts"], 0)
        self.assertEqual(report["errors"], ["context_too_large"])

    def test_output_limit_falls_back(self):
        self.provider.generate.return_value = ProviderReply("x" * 64001)
        self.assertTrue(investigate(self.event, self.provider)["used_fallback"])

    def test_real_provider_is_rejected_before_call(self):
        self.provider.simulated = False
        with self.assertRaises(ValueError):
            investigate(self.event, self.provider)
        self.provider.generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
