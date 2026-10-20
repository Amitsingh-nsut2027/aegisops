import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from event_schema import QueuedIncident
from incidents import build_incident_events
from investigator import run_investigation
from investigator_cli import load_event
from llm_provider import ProviderError


class InvestigatorTests(unittest.TestCase):
    def setUp(self):
        raw = build_incident_events([91, 92, 93], "workflow-test", "simulated/api",
                                    datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
        self.payload = json.loads(json.dumps(asdict(raw)))
        self.event = QueuedIncident.model_validate_json(json.dumps(self.payload))
        self.repository = Mock()
        self.row = {"event_id": self.event.event_id, "payload": self.payload}

    def test_workflow_exposes_missing_evidence_and_observable_trace(self):
        report = run_investigation(self.event)
        self.assertEqual(report["state"], "needs_evidence")
        self.assertEqual([c["status"] for c in report["evidence_checks"]],
                         ["available", "unavailable", "unavailable", "unavailable"])
        self.assertTrue(all(c["source"] == "not_connected" for c in report["evidence_checks"][1:]))
        self.assertEqual([step["sequence"] for step in report["trace"]], [1, 2, 3, 4, 5])
        self.assertEqual(report["trace"][-1]["status"], "needs_evidence")
        self.assertIsNone(report["analysis"]["result"]["root_cause"])
        self.assertLessEqual(report["started_at"], report["finished_at"])
        self.assertEqual(report["observed_at"], self.event.observed_at.isoformat())

    def test_replay_has_distinct_run_identity_but_same_event_and_result(self):
        first, second = run_investigation(self.event), run_investigation(self.event)
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["analysis"], second["analysis"])

    def test_fallback_is_visible_in_trace(self):
        provider = Mock()
        provider.name, provider.simulated = "broken-fake", True
        provider.generate.side_effect = ProviderError("private error")
        report = run_investigation(self.event, provider)
        summary_step = next(step for step in report["trace"] if step["step"] == "summarize_evidence")
        self.assertEqual(summary_step["status"], "fallback")
        self.assertEqual(report["state"], "needs_evidence")
        self.assertNotIn("private error", json.dumps(report))

    def test_invalid_constructed_event_is_rejected_before_provider(self):
        event = self.event.model_copy(update={"event_id": "0" * 64})
        provider = Mock()
        with self.assertRaises(ValueError):
            run_investigation(event, provider)
        provider.generate.assert_not_called()

    def test_select_by_id_or_latest_reads_only(self):
        self.repository.get_event.return_value = self.row
        self.assertEqual(load_event(self.repository, self.event.event_id), self.event)
        self.repository.get_event.assert_called_once_with(self.event.event_id)
        self.repository.list_events.assert_not_called()
        self.repository.list_events.return_value = [self.row]
        self.assertEqual(load_event(self.repository, None), self.event)
        self.repository.list_events.assert_called_once_with(limit=1, offset=0, source="simulator")

    def test_missing_event_does_not_substitute_another_event(self):
        self.repository.get_event.return_value = None
        with self.assertRaises(LookupError):
            load_event(self.repository, self.event.event_id)
        self.repository.list_events.assert_not_called()
        self.repository.list_events.return_value = []
        with self.assertRaises(LookupError):
            load_event(self.repository, None)

    def test_mismatched_saved_identity_is_rejected(self):
        self.repository.get_event.return_value = {**self.row, "event_id": "0" * 64}
        with self.assertRaises(ValueError):
            load_event(self.repository, self.event.event_id)


if __name__ == "__main__":
    unittest.main()
