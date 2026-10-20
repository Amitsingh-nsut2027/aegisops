import json
from urllib.parse import urlsplit

import boto3
from botocore.config import Config

QUEUE_NAME = "aegisops-local-incidents"
DLQ_NAME = "aegisops-local-incidents-dlq"


def local_sqs():
    # Deliberately independent of real AWS profiles or credentials.
    return boto3.client(
        "sqs", endpoint_url="http://moto:5000", region_name="us-east-1",
        aws_access_key_id="local-test", aws_secret_access_key="local-test",
        config=Config(connect_timeout=3, read_timeout=15,
                      retries={"mode": "standard", "max_attempts": 2}),
    )


def check_local_url(queue_url: str) -> None:
    parsed = urlsplit(queue_url)
    if parsed.scheme != "http" or parsed.hostname != "moto" or parsed.port != 5000:
        raise ValueError("This demo only accepts the local Moto queue endpoint")


def setup_queues(client) -> str:
    dead_letter = client.create_queue(QueueName=DLQ_NAME)["QueueUrl"]
    check_local_url(dead_letter)
    arn = client.get_queue_attributes(
        QueueUrl=dead_letter, AttributeNames=["QueueArn"],
    )["Attributes"]["QueueArn"]
    queue_url = client.create_queue(QueueName=QUEUE_NAME, Attributes={
        "VisibilityTimeout": "30",
        "ReceiveMessageWaitTimeSeconds": "2",
        "MessageRetentionPeriod": "86400",
        "RedrivePolicy": json.dumps({"deadLetterTargetArn": arn, "maxReceiveCount": "3"}),
    })["QueueUrl"]
    check_local_url(queue_url)
    return queue_url


def queue_url(client, name: str = QUEUE_NAME) -> str:
    url = client.get_queue_url(QueueName=name)["QueueUrl"]
    check_local_url(url)
    return url
