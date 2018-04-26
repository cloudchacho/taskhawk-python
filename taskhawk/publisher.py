import json
from decimal import Decimal
import logging

import boto3
from botocore.config import Config
from retrying import retry

from taskhawk.conf import settings
from taskhawk.consumer import get_queue_name, get_queue
from taskhawk.models import Message
from taskhawk import Priority


log = logging.getLogger(__name__)


def _get_sns_client():
    # https://botocore.readthedocs.io/en/stable/reference/config.html
    # seconds
    config = Config(
        connect_timeout=settings.AWS_CONNECT_TIMEOUT_S,
        read_timeout=settings.AWS_READ_TIMEOUT_S,
    )

    return boto3.client(
        'sns',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        endpoint_url=settings.AWS_ENDPOINT_SNS,
        config=config,
    )


def _get_sns_topic(priority: Priority) -> str:
    topic = f'arn:aws:sns:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:taskhawk-{settings.TASKHAWK_QUEUE.lower()}'
    if priority == Priority.high:
        topic += '-high-priority'
    elif priority == Priority.low:
        topic += '-low-priority'
    elif priority == Priority.bulk:
        topic += '-bulk'
    return topic


@retry(stop_max_attempt_number=3, stop_max_delay=3000)
def _publish_over_sns(topic: str, message_json: str, message_attributes: dict) -> None:
    # transform (http://boto.cloudhackers.com/en/latest/ref/sns.html#boto.sns.SNSConnection.publish)
    message_attributes = {
        k: {
            'DataType': 'String',
            'StringValue': str(v),
        } for k, v in message_attributes.items()
    }
    client = _get_sns_client()
    client.publish(
        TopicArn=topic,
        Message=message_json,
        MessageAttributes=message_attributes,
    )


@retry(stop_max_attempt_number=3, stop_max_delay=3000)
def _publish_over_sqs(queue, message_json: str, message_attributes: dict) -> dict:
    # transform (http://boto3.readthedocs.io/en/latest/reference/services/sqs.html#SQS.Client.send_message)
    message_attributes = {
        k: {
            'DataType': 'String',
            'StringValue': str(v),
        } for k, v in message_attributes.items()
    }
    return queue.send_message(
        MessageBody=message_json,
        MessageAttributes=message_attributes,
    )


def _log_published_message(message_body: dict) -> None:
    log.debug('Sent message', extra={'message_body': message_body})


def _decimal_json_default(obj):
    if isinstance(obj, Decimal):
        int_val = int(obj)
        if int_val == obj:
            return int_val
        else:
            return float(obj)
    raise TypeError


def _convert_to_json(data: dict) -> str:
    return json.dumps(data, default=_decimal_json_default)


def publish(message: Message) -> None:
    """
    Publishes a message on Taskhawk queue
    """
    message_body = message.as_dict()
    payload = _convert_to_json(message_body)

    if settings.IS_LAMBDA_APP:
        topic = _get_sns_topic(message.priority)
        _publish_over_sns(topic, payload, message.headers)
    else:
        queue_name = get_queue_name(message.priority)
        queue = get_queue(queue_name)
        _publish_over_sqs(queue, payload, message.headers)

    _log_published_message(message_body)
