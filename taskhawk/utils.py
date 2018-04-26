import boto3

from taskhawk.conf import settings
from taskhawk.consumer import get_queue_name
from taskhawk.models import Priority


def _get_sqs_client():
    return boto3.client(
        'sqs',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        endpoint_url=settings.AWS_ENDPOINT_SQS,
    )


def _get_queue_url(client, queue_name: str) -> str:
    response = client.get_queue_url(
        QueueName=queue_name,
    )
    return response['QueueUrl']


def extend_visibility_timeout(priority: Priority, receipt: str, visibility_timeout_s: int) -> None:
    """
    Extends visibility timeout of a message on a given priority queue for long running tasks.
    """

    queue_name = get_queue_name(priority)

    client = _get_sqs_client()

    queue_url = _get_queue_url(client, queue_name)

    client.change_message_visibility(
        QueueUrl=queue_url,
        ReceiptHandle=receipt,
        VisibilityTimeout=visibility_timeout_s,
    )
