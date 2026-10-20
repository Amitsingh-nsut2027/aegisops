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
from queue_transport import check_local_url
from queue_worker import consume_once, process_message


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.url = "http://moto:5000/123456789012/local-incidents"
        event = build_incident_events(
            [91, 92, 93], "queue-test", "simulated/api",
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )[0]
        self.payload = asdict(event)
        self.message = {"Body": json.dumps(self.payload), "ReceiptHandle": "local-receipt"}
        self.client = Mock()

    def test_acknowledges_after_successful_store(self):
        steps = []
        self.client.delete_message.side_effect = lambda **kwargs: steps.append("ack")
        with patch("queue_worker.store_events", side_effect=lambda *a: steps.append("commit") or 1):
            self.assertEqual(process_message(self.client, self.url, self.message, Mock()), 1)
        self.assertEqual(steps, ["commit", "ack"])

    def test_failed_store_does_not_acknowledge(self):
        with patch("queue_worker.store_events", side_effect=RuntimeError("database unavailable")):
            with self.assertRaises(RuntimeError):
                process_message(self.client, self.url, self.message, Mock())
        self.client.delete_message.assert_not_called()

    def test_duplicate_is_acknowledged(self):
        with patch("queue_worker.store_events", return_value=0):
            self.assertEqual(process_message(self.client, self.url, self.message, Mock()), 0)
        self.client.delete_message.assert_called_once_with(
            QueueUrl=self.url, ReceiptHandle="local-receipt",
        )

    def test_invalid_message_is_not_stored_or_acknowledged(self):
        self.message["Body"] = '{"source":"real-aws"}'
        with patch("queue_worker.store_events") as store:
            with self.assertRaises(ValueError):
                process_message(self.client, self.url, self.message, Mock())
        store.assert_not_called()
        self.client.delete_message.assert_not_called()

    def test_rejects_tampered_evidence_and_extra_fields(self):
        for changes in [{"cpu_evidence": [99, 99, 99]}, {"extra": "untrusted"},
                        {"observed_at": "2026-01-01T00:02:00"}, {"threshold": True},
                        {"sample": 1}, {"source": "aws"}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                QueuedIncident.model_validate_json(json.dumps({**self.payload, **changes}))

    def test_rejects_nonlocal_queue_urls(self):
        for url in ["https://sqs.us-east-1.amazonaws.com/123/queue",
                    "http://example.com:5000/queue", "http://moto:5001/queue"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                check_local_url(url)

    def test_empty_poll_is_successful(self):
        self.client.receive_message.return_value = {}
        with patch("queue_worker.store_events") as store:
            result = consume_once(self.client, self.url, Mock())
        self.assertEqual(result["received"], 0)
        self.assertEqual(result["failed"], 0)
        store.assert_not_called()


if __name__ == "__main__":
    unittest.main()
