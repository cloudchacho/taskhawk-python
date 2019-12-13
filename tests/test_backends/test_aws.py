import json
import uuid
from unittest import mock

import funcy
import pytest

try:
    from taskhawk.backends.aws import AWSMetadata
except ImportError:
    pass
from taskhawk.backends.exceptions import PartialFailure
from taskhawk.conf import settings
from taskhawk.models import Priority

aws = pytest.importorskip('taskhawk.backends.aws')


class TestSNSPublisher:
    @pytest.mark.parametrize(
        'priority,topic',
        [
            [Priority.default, 'taskhawk-myqueue'],
            [Priority.high, 'taskhawk-myqueue-high-priority'],
            [Priority.low, 'taskhawk-myqueue-low-priority'],
            [Priority.bulk, 'taskhawk-myqueue-bulk'],
        ],
    )
    def test_constructor_topic_name(self, priority, topic, mock_boto3, settings):
        settings.TASKHAWK_QUEUE = 'myqueue'
        sns_publisher = aws.AWSSNSPublisherBackend(priority=priority)
        assert sns_publisher.topic_name == f'arn:aws:sns:DUMMY_REGION:DUMMY_ACCOUNT:{topic}'

    def test_publish_success(self, mock_boto3, message):
        sns_publisher = aws.AWSSNSPublisherBackend(priority=message.priority)
        queue = mock.MagicMock()
        sns_publisher.sns_client.publish.get_queue_by_name = mock.MagicMock(return_value=queue)

        sns_publisher.publish(message)

        mock_boto3.client.assert_called_once_with(
            'sns',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN,
            endpoint_url=settings.AWS_ENDPOINT_SQS,
            config=mock.ANY,
        )
        topic = (
            f'arn:aws:sns:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:taskhawk-{settings.TASKHAWK_QUEUE.lower()}'
        )
        sns_publisher.sns_client.publish.assert_called_once_with(
            TopicArn=topic,
            Message=sns_publisher.message_payload(message.as_dict()),
            MessageAttributes={k: {'DataType': 'String', 'StringValue': str(v)} for k, v in message.headers.items()},
        )

    @mock.patch('tests.tasks._send_email', autospec=True)
    def test_sync_mode(self, mock_send_email, mock_boto3, message, settings):
        settings.TASKHAWK_PUBLISHER_BACKEND = 'taskhawk.backends.aws.AWSSNSPublisherBackend'
        settings.TASKHAWK_CONSUMER_BACKEND = 'taskhawk.backends.aws.AWSSQSConsumerBackend'
        settings.TASKHAWK_SYNC = True

        aws_publisher = aws.AWSSNSPublisherBackend(priority=message.priority)
        aws_publisher.publish(message)

        mock_send_email.assert_called_once()
        assert mock_send_email.call_args[0] == tuple(message.args)
        assert funcy.project(mock_send_email.call_args[1], message.kwargs.keys()) == message.kwargs
        assert mock_send_email.call_args[1]['headers'] == message.headers
        assert mock_send_email.call_args[1]['metadata'] == message.metadata


pre_process_hook = mock.MagicMock()
post_process_hook = mock.MagicMock()


@pytest.fixture(name='reset_mocks')
def _reset_mocks():
    yield
    pre_process_hook.reset_mock()
    post_process_hook.reset_mock()


class TestSQSConsumer:
    @pytest.fixture()
    def consumer(self):
        return aws.AWSSQSConsumerBackend(priority=Priority.default)

    @pytest.mark.parametrize(
        'priority,queue',
        [
            [Priority.default, 'TASKHAWK-MYQUEUE'],
            [Priority.high, 'TASKHAWK-MYQUEUE-HIGH-PRIORITY'],
            [Priority.low, 'TASKHAWK-MYQUEUE-LOW-PRIORITY'],
            [Priority.bulk, 'TASKHAWK-MYQUEUE-BULK'],
        ],
    )
    def test_constructor_queue_name(self, priority, queue, mock_boto3, settings):
        settings.TASKHAWK_QUEUE = 'myqueue'
        sqs_publisher = aws.AWSSQSConsumerBackend(priority=priority)
        assert sqs_publisher.queue_name == queue

    def test_client_and_resource_instantiation(self, mock_boto3, consumer):
        # make sure client and resource are initialized
        consumer.sqs_client
        consumer.sqs_resource
        mock_boto3.resource.assert_called_once_with(
            'sqs',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN,
            endpoint_url=settings.AWS_ENDPOINT_SQS,
        )
        mock_boto3.client.assert_called_once_with(
            'sqs',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY,
            aws_secret_access_key=settings.AWS_SECRET_KEY,
            aws_session_token=settings.AWS_SESSION_TOKEN,
            endpoint_url=settings.AWS_ENDPOINT_SQS,
        )

    def test_pull_messages(self, mock_boto3, consumer):
        num_messages = 1
        visibility_timeout = 10
        queue = mock.MagicMock()
        consumer.sqs_resource.get_queue_by_name = mock.MagicMock(return_value=queue)

        consumer.pull_messages(num_messages, visibility_timeout)

        consumer.sqs_resource.get_queue_by_name.assert_called_once_with(QueueName=consumer.queue_name)
        queue.receive_messages.assert_called_once_with(
            MaxNumberOfMessages=1,
            MessageAttributeNames=['All'],
            VisibilityTimeout=visibility_timeout,
            WaitTimeSeconds=consumer.WAIT_TIME_SECONDS,
        )

    def test_extend_visibility_timeout(self, mock_boto3, consumer):
        visibility_timeout_s = 10
        receipt = "receipt"
        consumer.sqs_client.get_queue_url = mock.MagicMock(return_value={"QueueUrl": "DummyQueueUrl"})

        consumer.extend_visibility_timeout(visibility_timeout_s, AWSMetadata(receipt))

        consumer.sqs_client.get_queue_url.assert_called_once_with(QueueName=consumer.queue_name)
        consumer.sqs_client.change_message_visibility.assert_called_once_with(
            QueueUrl='DummyQueueUrl', ReceiptHandle='receipt', VisibilityTimeout=10
        )

    def test_success_requeue_dead_letter(self, mock_boto3):
        consumer = aws.AWSSQSConsumerBackend(priority=Priority.default, dlq=True)
        num_messages = 3
        visibility_timeout = 4

        messages = [mock.MagicMock() for _ in range(num_messages)]
        consumer.pull_messages = mock.MagicMock(side_effect=iter([messages, None]))

        mock_queue, mock_dlq = mock.MagicMock(), mock.MagicMock()
        mock_queue.send_messages.return_value = {'Failed': []}
        consumer.sqs_resource.get_queue_by_name = mock.MagicMock(side_effect=iter([mock_queue, mock_dlq]))
        mock_dlq.delete_messages.return_value = {'Failed': []}

        consumer.requeue_dead_letter(num_messages=num_messages, visibility_timeout=visibility_timeout)

        consumer.sqs_resource.get_queue_by_name.assert_has_calls(
            [mock.call(QueueName=f'TASKHAWK-{settings.TASKHAWK_QUEUE}'), mock.call(QueueName=consumer.queue_name)]
        )

        consumer.pull_messages.assert_has_calls(
            [
                mock.call(num_messages=num_messages, visibility_timeout=visibility_timeout),
                mock.call(num_messages=num_messages, visibility_timeout=visibility_timeout),
            ]
        )
        mock_queue.send_messages.assert_called_once_with(
            Entries=[
                {
                    'Id': queue_message.message_id,
                    'MessageBody': queue_message.body,
                    'MessageAttributes': queue_message.message_attributes,
                }
                for queue_message in messages
            ]
        )
        mock_dlq.delete_messages.assert_called_once_with(
            Entries=[
                {'Id': queue_message.message_id, 'ReceiptHandle': queue_message.receipt_handle}
                for queue_message in messages
            ]
        )

    def test_partial_failure_requeue_dead_letter(self, mock_boto3, consumer):
        num_messages = 1
        visibility_timeout = 4
        queue_name = "TASKHAWK-DEV-RTEP"

        messages = [mock.MagicMock() for _ in range(num_messages)]
        consumer.pull_messages = mock.MagicMock(side_effect=iter([messages, None]))
        dlq_name = f'{queue_name}-DLQ'

        mock_queue, mock_dlq = mock.MagicMock(), mock.MagicMock()
        mock_queue.attributes = {'RedrivePolicy': json.dumps({'deadLetterTargetArn': dlq_name})}
        mock_queue.send_messages.return_value = {'Successful': ['success_id'], 'Failed': ["fail_id"]}
        consumer._get_queue_by_name = mock.MagicMock(side_effect=iter([mock_queue, mock_dlq]))

        with pytest.raises(PartialFailure):
            consumer.requeue_dead_letter(num_messages=num_messages, visibility_timeout=visibility_timeout)

    def test_fetch_and_process_messages_success(self, mock_boto3, settings, message_data, consumer, reset_mocks):
        settings.TASKHAWK_PRE_PROCESS_HOOK = 'tests.test_backends.test_aws.pre_process_hook'
        settings.TASKHAWK_POST_PROCESS_HOOK = 'tests.test_backends.test_aws.post_process_hook'
        num_messages = 3
        visibility_timeout = 4
        queue = mock.MagicMock()
        consumer.sqs_resource.get_queue_by_name = mock.MagicMock(return_value=queue)

        queue_message = mock.MagicMock()
        queue_message.body = json.dumps(message_data)
        queue_message.receipt_handle = "dummy receipt"
        queue.receive_messages = mock.MagicMock(return_value=[queue_message])
        message_mock = mock.MagicMock()
        consumer._build_message = mock.MagicMock(return_value=message_mock)
        consumer.process_message = mock.MagicMock(wraps=consumer.process_message)
        consumer.message_handler = mock.MagicMock(wraps=consumer.message_handler)

        consumer.fetch_and_process_messages(num_messages, visibility_timeout)

        consumer.sqs_resource.get_queue_by_name.assert_called_once_with(QueueName=consumer.queue_name)
        queue.receive_messages.assert_called_once_with(
            MaxNumberOfMessages=num_messages,
            MessageAttributeNames=['All'],
            VisibilityTimeout=visibility_timeout,
            WaitTimeSeconds=consumer.WAIT_TIME_SECONDS,
        )
        consumer.process_message.assert_called_once_with(queue_message)
        consumer.message_handler.assert_called_once_with(queue_message.body, AWSMetadata(queue_message.receipt_handle))
        message_mock.call_task.assert_called_once_with()
        queue_message.delete.assert_called_once_with()
        pre_process_hook.assert_called_once_with(sqs_queue_message=queue_message)
        post_process_hook.assert_called_once_with(sqs_queue_message=queue_message)


class TestSNSConsumer:
    @mock.patch('taskhawk.backends.aws.AWSSNSConsumerBackend.process_message')
    def test_process_messages(self, mock_process_message):
        records = mock.Mock(), mock.Mock()
        event = {'Records': records}

        consumer = aws.AWSSNSConsumerBackend()
        consumer.process_messages(event)

        mock_process_message.assert_has_calls([mock.call(r) for r in records])

    def test_success_process_message(self, mock_boto3, settings, reset_mocks):
        settings.TASKHAWK_PRE_PROCESS_HOOK = 'tests.test_backends.test_aws.pre_process_hook'
        settings.TASKHAWK_POST_PROCESS_HOOK = 'tests.test_backends.test_aws.post_process_hook'
        consumer = aws.AWSSNSConsumerBackend()
        # copy from https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns
        mock_record = {
            "EventVersion": "1.0",
            "EventSubscriptionArn": "arn",
            "EventSource": "aws:sns",
            "Sns": {
                "SignatureVersion": "1",
                "Timestamp": "1970-01-01T00:00:00.000Z",
                "Signature": "EXAMPLE",
                "SigningCertUrl": "EXAMPLE",
                "MessageId": "95df01b4-ee98-5cb9-9903-4c221d41eb5e",
                "Message": "Hello from SNS!",
                "MessageAttributes": {
                    "request_id": {"Type": "String", "Value": str(uuid.uuid4())},
                    "TestBinary": {"Type": "Binary", "Value": "TestBinary"},
                },
                "Type": "Notification",
                "UnsubscribeUrl": "EXAMPLE",
                "TopicArn": "arn",
                "Subject": "TestInvoke",
            },
        }
        message_mock = mock.MagicMock()
        consumer._build_message = mock.MagicMock(return_value=message_mock)

        consumer.process_message(mock_record)

        pre_process_hook.assert_called_once_with(sns_record=mock_record)
        post_process_hook.assert_called_once_with(sns_record=mock_record)
        message_mock.call_task.assert_called_once_with()
