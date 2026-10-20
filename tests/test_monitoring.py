import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from incidents import build_incident_events
from simulator import detect_cpu_alerts


class MonitoringTests(unittest.TestCase):
    def setUp(self):
        self.samples = [91, 92, 93, 94, 95, 90, 91, 92, 93]
        self.start = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def events(self, samples=None, **kwargs):
        options = dict(scenario_id="test-v1", resource_id="simulated/api",
                       start_time=self.start)
        options.update(kwargs)
        return build_incident_events(self.samples if samples is None else samples, **options)

    def test_detector_baseline_and_reset(self):
        for samples, expected in [([35, 42, 91, 45, 92, 95, 96, 40], [7]),
                                  (self.samples, [3, 9])]:
            with self.subTest(samples=samples):
                records = detect_cpu_alerts(samples)
                self.assertEqual([r["sample"] for r in records if r["alert"]], expected)

    def test_only_alerts_become_events_with_evidence(self):
        events = self.events()
        self.assertEqual([e.sample for e in events], [3, 9])
        self.assertEqual([e.cpu_evidence for e in events], [(91., 92., 93.)] * 2)
        self.assertTrue(all(e.source == "simulator" for e in events))
        self.assertEqual(events[0].observed_at, "2026-01-01T00:02:00+00:00")

    def test_replay_ids_are_stable_and_resource_scoped(self):
        original = [e.event_id for e in self.events()]
        self.assertEqual(original, [e.event_id for e in self.events()])
        self.assertEqual(len(set(original)), 2)
        self.assertNotEqual(original, [e.event_id for e in self.events(resource_id="simulated/other")])
        self.assertNotEqual(original, [e.event_id for e in self.events(scenario_id="another-run")])

    def test_normal_and_empty_inputs_emit_no_events(self):
        self.assertEqual(self.events([]), [])
        self.assertEqual(self.events([30, 40, 90]), [])

    def test_invalid_input_is_rejected(self):
        for value in [-1, 101, float("nan"), float("inf"), True, "95"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.events([value])
        for options in [dict(required_samples=0), dict(required_samples=True),
                        dict(threshold=101), dict(scenario_id=" "),
                        dict(resource_id=""), dict(start_time=datetime(2026, 1, 1))]:
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.events(**options)

    def test_custom_window_and_fresh_calls(self):
        for _ in range(2):
            self.assertEqual([e.sample for e in self.events([81, 82], threshold=80,
                                                          required_samples=2)], [2])


if __name__ == "__main__":
    unittest.main()
