import json
import logging
import typing
from concurrent.futures import Future
from typing import Optional
from unittest import mock

import boto3
import funcy
from botocore.config import Config
from mypy_boto3_sns import SNSClient
from mypy_boto3_sqs import SQSClient
from mypy_boto3_sqs.service_resource import SQSServiceResource
from retrying import retry

from taskhawk.backends.base import (
    TaskhawkConsumerBaseBackend,
    TaskhawkPublisherBaseBackend,
)
from taskhawk.backends.exceptions import PartialFailure
from taskhawk.conf import settings
from taskhawk.models import Message, Priority


logger = logging.getLogger(__name__)


class AWSMetadata:
    def __init__(self, receipt):
        self._receipt = receipt

    @property
    def receipt(self):
        return self._receipt

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, AWSMetadata):
            return False
        return self._receipt == o._receipt

    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f'AWSMetadata(receipt={self._receipt})'

    def __hash__(self) -> int:
        return hash((self._receipt,))


class AWSSNSPublisherBackend(TaskhawkPublisherBaseBackend):
    def __init__(self, priority: Priority):
        self._sns_client: Optional[SNSClient] = None
        self.topic_name = (
            f'arn:aws:sns:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:taskhawk-{settings.TASKHAWK_QUEUE.lower()}'
            f'{self.get_priority_suffix(priority)}'
        )

    @property
    def sns_client(self):
        if self._sns_client is None:
            config = Config(connect_timeout=settings.AWS_CONNECT_TIMEOUT_S, read_timeout=settings.AWS_READ_TIMEOUT_S)
            self._sns_client = boto3.client(
                'sns',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SECRET_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN,
                endpoint_url=settings.AWS_ENDPOINT_SNS,
                config=config,
            )
        return self._sns_client

    @staticmethod
    def get_priority_suffix(priority: Priority) -> str:
        if priority is Priority.high:
            return '-high-priority'
        elif priority is Priority.low:
            return '-low-priority'
        elif priority is Priority.bulk:
            return '-bulk'
        return ''

    @retry(stop_max_attempt_number=3, stop_max_delay=3000)
    def _publish_over_sns(self, topic: str, message_json: str, message_attributes: typing.Mapping) -> str:
        # transform (http://boto.cloudhackers.com/en/latest/ref/sns.html#boto.sns.SNSConnection.publish)
        message_attributes = {k: {'DataType': 'String', 'StringValue': str(v)} for k, v in message_attributes.items()}
        response = self.sns_client.publish(TopicArn=topic, Message=message_json, MessageAttributes=message_attributes)
        return response['PublishResponse']['PublishResult']['MessageId']

    def _mock_queue_message(self, message: Message) -> mock.Mock:
        sqs_message = mock.Mock()
        sqs_message.body = json.dumps(message.as_dict())
        sqs_message.receipt_handle = 'test-receipt'
        return sqs_message

    def _publish(
        self,
        message: Message,
        payload: str,
        headers: typing.Optional[typing.Mapping] = None,
    ) -> typing.Union[str, Future]:
        return self._publish_over_sns(self.topic_name, payload, headers or {})


class AWSSQSConsumerBackend(TaskhawkConsumerBaseBackend):
    WAIT_TIME_SECONDS = 20

    def __init__(self, priority: Priority, dlq=False):

        self._sqs_resource: Optional[SQSServiceResource] = None
        self._sqs_client: Optional[SQSClient] = None
        self.queue_name = (
            f'TASKHAWK-{settings.TASKHAWK_QUEUE.upper()}{self.get_priority_suffix(priority)}{"-DLQ" if dlq else ""}'
        )

    @property
    def sqs_resource(self):
        if self._sqs_resource is None:
            self._sqs_resource = boto3.resource(
                'sqs',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SECRET_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN,
                endpoint_url=settings.AWS_ENDPOINT_SQS,
            )
        return self._sqs_resource

    @property
    def sqs_client(self):
        if self._sqs_client is None:
            self._sqs_client = boto3.client(
                'sqs',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY,
                aws_secret_access_key=settings.AWS_SECRET_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN,
                endpoint_url=settings.AWS_ENDPOINT_SQS,
            )
        return self._sqs_client

    @staticmethod
    def get_priority_suffix(priority: Priority) -> str:
        if priority is Priority.high:
            return '-HIGH-PRIORITY'
        elif priority is Priority.low:
            return '-LOW-PRIORITY'
        elif priority is Priority.bulk:
            return '-BULK'
        return ''

    def _get_queue(self):
        return self.sqs_resource.get_queue_by_name(QueueName=self.queue_name)

    def pull_messages(self, num_messages: int = 1, visibility_timeout: Optional[int] = None) -> typing.List:
        params = {
            'MaxNumberOfMessages': num_messages,
            'WaitTimeSeconds': self.WAIT_TIME_SECONDS,
            'MessageAttributeNames': ['All'],
        }
        if visibility_timeout is not None:
            params['VisibilityTimeout'] = visibility_timeout
        return self._get_queue().receive_messages(**params)

    def process_message(self, queue_message) -> None:
        message_json = queue_message.body
        receipt = queue_message.receipt_handle
        self.message_handler(message_json, AWSMetadata(receipt))

    def delete_message(self, queue_message) -> None:
        queue_message.delete()

    def extend_visibility_timeout(self, visibility_timeout_s: int, metadata: AWSMetadata) -> None:
        """
        Extends visibility timeout of a message on a given priority queue for long running tasks.
        """
        receipt = metadata.receipt
        queue_url = self.sqs_client.get_queue_url(QueueName=self.queue_name)['QueueUrl']
        self.sqs_client.change_message_visibility(
            QueueUrl=queue_url, ReceiptHandle=receipt, VisibilityTimeout=visibility_timeout_s
        )

    def requeue_dead_letter(self, num_messages: int = 10, visibility_timeout: Optional[int] = None) -> None:
        """
        Re-queues everything in the Taskhawk DLQ back into the Taskhawk queue.

        :param num_messages: Maximum number of messages to fetch in one SQS call. Defaults to 10.
        :param visibility_timeout: The number of seconds the message should remain invisible to other queue readers.
        Defaults to None, which is queue default
        """
        sqs_queue = self.sqs_resource.get_queue_by_name(QueueName=f'TASKHAWK-{settings.TASKHAWK_QUEUE}')
        dead_letter_queue = self._get_queue()

        logging.info("Re-queueing messages from {} to {}".format(dead_letter_queue.url, sqs_queue.url))
        while True:
            queue_messages = self.pull_messages(num_messages=num_messages, visibility_timeout=visibility_timeout)
            if not queue_messages:
                break

            logging.info("got {} messages from dlq".format(len(queue_messages)))

            result = sqs_queue.send_messages(
                Entries=[
                    funcy.merge(
                        {'Id': queue_message.message_id, 'MessageBody': queue_message.body},
                        {'MessageAttributes': queue_message.message_attributes}
                        if queue_message.message_attributes
                        else {},
                    )
                    for queue_message in queue_messages
                ]
            )
            if result.get('Failed'):
                raise PartialFailure(result)

            dead_letter_queue.delete_messages(
                Entries=[
                    {'Id': message.message_id, 'ReceiptHandle': message.receipt_handle} for message in queue_messages
                ]
            )

            logging.info("Re-queued {} messages".format(len(queue_messages)))

    @staticmethod
    def pre_process_hook_kwargs(queue_message) -> dict:
        return {'sqs_queue_message': queue_message}

    @staticmethod
    def post_process_hook_kwargs(queue_message) -> dict:
        return {'sqs_queue_message': queue_message}


class AWSSNSConsumerBackend(TaskhawkConsumerBaseBackend):
    def extend_visibility_timeout(self, visibility_timeout_s: int, metadata) -> None:
        raise RuntimeError("invalid operation for backend")

    def requeue_dead_letter(self, num_messages: int = 10, visibility_timeout: Optional[int] = None) -> None:
        raise RuntimeError("invalid operation for backend")

    def pull_messages(self, num_messages: int = 1, visibility_timeout: Optional[int] = None) -> typing.List:
        raise RuntimeError("invalid operation for backend")

    def delete_message(self, queue_message) -> None:
        raise RuntimeError("invalid operation for backend")

    def process_messages(self, lambda_event):
        for record in lambda_event['Records']:
            self.process_message(record)

    def process_message(self, queue_message) -> None:
        settings.TASKHAWK_PRE_PROCESS_HOOK(sns_record=queue_message)
        message_json = queue_message['Sns']['Message']
        self.message_handler(message_json, None)
        settings.TASKHAWK_POST_PROCESS_HOOK(sns_record=queue_message)
