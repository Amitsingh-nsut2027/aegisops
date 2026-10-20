import json

from pydantic import ValidationError
from sqlalchemy.engine import Engine

from event_schema import QueuedIncident
from persist_incidents import store_events
from queue_transport import check_local_url


def process_message(client, url: str, message: dict, engine: Engine) -> int:
    check_local_url(url)
    event = QueuedIncident.model_validate_json(message["Body"]).to_event()
    inserted = store_events(engine, [event])  # Returns only after commit.
    client.delete_message(QueueUrl=url, ReceiptHandle=message["ReceiptHandle"])
    return inserted


def consume_once(client, url: str, engine: Engine) -> dict:
    check_local_url(url)
    messages = client.receive_message(
        QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=2,
        VisibilityTimeout=30,
    ).get("Messages", [])
    summary = {"received": len(messages), "inserted": 0,
               "duplicates": 0, "acknowledged": 0, "failed": 0}
    for message in messages:
        try:
            inserted = process_message(client, url, message, engine)
        except Exception as error:
            # Leave the message unacknowledged for retry or DLQ redrive.
            summary["failed"] += 1
            reason = "invalid_event" if isinstance(error, ValidationError) else type(error).__name__
            print(json.dumps({"event": "message_failed", "reason": reason}), flush=True)
        else:
            summary["inserted"] += inserted
            summary["duplicates"] += 1 - inserted
            summary["acknowledged"] += 1
    return summary
