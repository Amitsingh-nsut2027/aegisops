"""Local Moto integration checks; create and remove only isolated test queues."""
import json
import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from incidents import build_incident_events
from queue_transport import check_local_url, local_sqs
from queue_worker import process_message


class LocalQueueTests(unittest.TestCase):
    def setUp(self):
        self.client = local_sqs()
        suffix = uuid4().hex
        self.urls = []
        self.dlq = self.create(f"aegisops-test-dlq-{suffix}")
        arn = self.client.get_queue_attributes(
            QueueUrl=self.dlq, AttributeNames=["QueueArn"],
        )["Attributes"]["QueueArn"]
        self.queue = self.create(f"aegisops-test-{suffix}", {
            "RedrivePolicy": json.dumps({"deadLetterTargetArn": arn, "maxReceiveCount": "3"}),
        })
        event = build_incident_events([91, 92, 93], suffix, "simulated/test",
                                      datetime(2026, 1, 1, tzinfo=timezone.utc))[0]
        self.body = json.dumps(asdict(event))

    def create(self, name, attributes=None):
        url = self.client.create_queue(QueueName=name, Attributes=attributes or {})["QueueUrl"]
        check_local_url(url)
        self.urls.append(url)
        return url

    def tearDown(self):
        for url in reversed(self.urls):
            self.client.delete_queue(QueueUrl=url)
        self.client.close()

    def receive(self, url):
        return self.client.receive_message(
            QueueUrl=url, VisibilityTimeout=0, WaitTimeSeconds=0,
        ).get("Messages", [])

    def test_database_failure_keeps_message_for_retry(self):
        self.client.send_message(QueueUrl=self.queue, MessageBody=self.body)
        message = self.receive(self.queue)[0]
        with patch("queue_worker.store_events", side_effect=RuntimeError("simulated outage")):
            with self.assertRaises(RuntimeError):
                process_message(self.client, self.queue, message, Mock())
        self.assertEqual(self.receive(self.queue)[0]["MessageId"], message["MessageId"])

    def test_successful_commit_acknowledges_message(self):
        self.client.send_message(QueueUrl=self.queue, MessageBody=self.body)
        with patch("queue_worker.store_events", return_value=1):
            process_message(self.client, self.queue, self.receive(self.queue)[0], Mock())
        self.assertEqual(self.receive(self.queue), [])

    def test_poison_message_moves_to_dead_letter_queue(self):
        self.client.send_message(QueueUrl=self.queue, MessageBody="invalid-event")
        for _ in range(3):
            message = self.receive(self.queue)[0]
            with self.assertRaises(ValueError):
                process_message(self.client, self.queue, message, Mock())
        self.assertEqual(self.receive(self.queue), [])
        self.assertEqual(self.receive(self.dlq)[0]["Body"], "invalid-event")


if __name__ == "__main__":
    unittest.main()
