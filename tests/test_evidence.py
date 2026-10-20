import json
import sys
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from event_schema import QueuedIncident
from evidence import EvidenceRecord, evidence_identity, traffic_surge_fixture, validate_evidence
from incidents import build_incident_events
from investigator import run_investigation
from llm_provider import ProviderReply, deterministic_summary, investigate


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        raw = build_incident_events([91, 92, 93], "evidence-test", "simulated/api",
                                    datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
        self.event = QueuedIncident.model_validate_json(json.dumps(asdict(raw)))
        self.evidence = traffic_surge_fixture(self.event)

    def altered(self, **updates):
        values = self.evidence[0].model_dump(mode="json", exclude={"evidence_id"})
        values.update(updates)
        return EvidenceRecord.model_validate_json(json.dumps(
            {**values, "evidence_id": evidence_identity(values)}))

    def test_fixture_is_repeatable_and_explicitly_simulated(self):
        self.assertEqual(self.evidence, traffic_surge_fixture(self.event))
        self.assertEqual(validate_evidence(self.event, self.evidence), self.evidence)
        self.assertTrue(all(item.simulated and item.source.startswith("scripted-fixture/") for item in self.evidence))

    def test_tampered_payload_is_rejected(self):
        values = self.evidence[0].model_dump(mode="json")
        values["detail"] = "tampered"
        with self.assertRaises(ValueError):
            EvidenceRecord.model_validate_json(json.dumps(values))

    def test_equivalent_utc_serializations_keep_same_identity(self):
        values = self.evidence[0].model_dump(mode="json")
        values["observed_at"] = self.evidence[0].observed_at.isoformat()
        restored = EvidenceRecord.model_validate_json(json.dumps(values))
        self.assertEqual(restored.evidence_id, self.evidence[0].evidence_id)

    def test_other_event_or_resource_is_rejected_before_provider(self):
        for change in [{"event_id": "0" * 64}, {"resource_id": "simulated/other"}]:
            with self.subTest(change=change):
                provider = Mock()
                with self.assertRaises(ValueError):
                    run_investigation(self.event, provider, [self.altered(**change)])
                provider.generate.assert_not_called()

    def test_stale_and_future_evidence_is_rejected(self):
        for delta in [-6, 1]:
            item = self.altered(observed_at=(self.event.observed_at + timedelta(minutes=delta)).isoformat())
            with self.assertRaises(ValueError):
                validate_evidence(self.event, [item])

    def test_duplicate_kinds_and_excess_records_rejected(self):
        for items in [[self.evidence[0], self.evidence[0]], self.evidence + [self.evidence[0]]]:
            with self.assertRaises(ValueError):
                validate_evidence(self.event, items)

    def test_enriched_report_contains_provenance_and_citations_without_causal_claim(self):
        report = run_investigation(self.event, evidence=self.evidence)
        self.assertTrue(all(check["status"] == "available" for check in report["evidence_checks"]))
        self.assertEqual(len(report["supplemental_evidence"]), 3)
        result = report["analysis"]["result"]
        self.assertEqual(set(result["evidence_ids"]), {self.event.event_id, *(e.evidence_id for e in self.evidence)})
        self.assertIsNone(result["root_cause"])
        self.assertEqual(report["state"], "needs_evidence")

    def test_supplemental_evidence_reaches_provider_and_unknown_citation_falls_back(self):
        provider = Mock()
        provider.name, provider.simulated = "test-fake", True
        output = deterministic_summary(self.event).model_dump()
        output["evidence_ids"] = [self.event.event_id, "0" * 64]
        provider.generate.return_value = ProviderReply(json.dumps(output))
        report = investigate(self.event, provider, self.evidence)
        self.assertTrue(report["used_fallback"])
        context = json.loads(provider.generate.call_args.args[0].context_json)
        self.assertEqual(len(context["supplemental_evidence"]), 3)

    def test_default_workflow_does_not_fabricate_additional_evidence(self):
        report = run_investigation(self.event)
        self.assertEqual(report["supplemental_evidence"], [])
        self.assertEqual([check["status"] for check in report["evidence_checks"]],
                         ["available", "unavailable", "unavailable", "unavailable"])
