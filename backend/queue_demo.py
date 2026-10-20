import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone

from database import database_engine
from incidents import build_incident_events
from queue_transport import DLQ_NAME, local_sqs, queue_url, setup_queues
from queue_worker import consume_once


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-only simulated SQS pipeline")
    parser.add_argument("command", choices=["publish", "work", "status"])
    parser.add_argument("--scenario-id", default="cpu-spike-demo-v1")
    args = parser.parse_args()
    client = local_sqs()
    try:
        if args.command == "publish":
            url = setup_queues(client)
            events = build_incident_events(
                [91, 92, 93, 94, 95, 90, 91, 92, 93],
                scenario_id=args.scenario_id, resource_id="simulated/ecs/api-service",
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
            for event in events:
                client.send_message(QueueUrl=url, MessageBody=json.dumps(asdict(event)))
            result = {"source": "simulator", "published": len(events)}
        elif args.command == "work":
            engine = database_engine()
            try:
                result = consume_once(client, queue_url(client), engine)
            finally:
                engine.dispose()
        else:
            result = {}
            for label, name in [("queue", "aegisops-local-incidents"), ("dlq", DLQ_NAME)]:
                result[label] = client.get_queue_attributes(
                    QueueUrl=queue_url(client, name), AttributeNames=[
                        "ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
                )["Attributes"]
        print(json.dumps(result))
        if result.get("failed", 0):
            raise SystemExit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
