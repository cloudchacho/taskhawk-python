import json
from time import time
from unittest import mock

import arrow
import funcy
import pytest

try:
    from google.api_core.exceptions import ServiceUnavailable
    from google.cloud.pubsub_v1.types import PubsubMessage, ReceivedMessage
    from taskhawk.backends.gcp import GoogleMetadata
except ImportError:
    pass
from taskhawk.conf import settings
from taskhawk.models import Priority

gcp = pytest.importorskip('taskhawk.backends.gcp')


@pytest.fixture(autouse=True, name="gcp_settings")
def _gcp_settings(settings):
    settings.GOOGLE_APPLICATION_CREDENTIALS = "DUMMY_GOOGLE_APPLICATION_CREDENTIALS"
    settings.TASKHAWK_PUBLISHER_BACKEND = "taskhawk.backends.gcp.GooglePubSubPublisherBackend"
    settings.TASKHAWK_CONSUMER_BACKEND = "taskhawk.backends.gcp.GooglePubSubConsumerBackend"
    settings.GOOGLE_CLOUD_PROJECT = "DUMMY_PROJECT_ID"
    settings.GOOGLE_PUBSUB_READ_TIMEOUT_S = 5
    yield settings


class TestPubSubPublisher:
    @pytest.mark.parametrize(
        'priority,topic',
        [
            [Priority.default, 'taskhawk-myqueue'],
            [Priority.high, 'taskhawk-myqueue-high-priority'],
            [Priority.low, 'taskhawk-myqueue-low-priority'],
            [Priority.bulk, 'taskhawk-myqueue-bulk'],
        ],
    )
    def test_constructor_topic_path(self, priority, topic, mock_pubsub_v1):
        settings.TASKHAWK_QUEUE = 'myqueue'
        gcp_publisher = gcp.GooglePubSubPublisherBackend(priority=priority)
        assert gcp_publisher._topic_path == f'projects/DUMMY_PROJECT_ID/topics/{topic}'

    def test_constructor(self, mock_pubsub_v1):
        gcp_publisher = gcp.GooglePubSubPublisherBackend(priority=Priority.default)
        assert gcp_publisher.publisher == mock_pubsub_v1.PublisherClient()

    def test_publish_success(self, mock_pubsub_v1, message):
        gcp_publisher = gcp.GooglePubSubPublisherBackend(priority=message.priority)
        message_data = json.dumps(message.as_dict())

        gcp_publisher.publish(message)

        gcp_publisher.publisher.publish.assert_called_once_with(
            gcp_publisher._topic_path, data=message_data.encode(), **message.headers
        )

    def test_async_publish_success(self, mock_pubsub_v1, message):
        gcp_publisher = gcp.GooglePubSubAsyncPublisherBackend(priority=message.priority)
        message_data = json.dumps(message.as_dict())

        future = gcp_publisher.publish(message)

        assert future == gcp_publisher.publisher.publish.return_value

        gcp_publisher.publisher.publish.assert_called_once_with(
            gcp_publisher._topic_path, data=message_data.encode(), **message.headers
        )

    @mock.patch('tests.tasks._send_email', autospec=True)
    def test_sync_mode(self, mock_send_email, mock_pubsub_v1, message, gcp_settings):
        gcp_settings.TASKHAWK_SYNC = True

        gcp_publisher = gcp.GooglePubSubPublisherBackend(priority=message.priority)
        gcp_publisher.publish(message)

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


@pytest.fixture(name='gcp_consumer')
def _gcp_consumer():
    return gcp.GooglePubSubConsumerBackend(priority=Priority.default)


class TestGCPConsumer:
    @pytest.mark.parametrize(
        'priority,queue',
        [
            [Priority.default, 'taskhawk-myqueue'],
            [Priority.high, 'taskhawk-myqueue-high-priority'],
            [Priority.low, 'taskhawk-myqueue-low-priority'],
            [Priority.bulk, 'taskhawk-myqueue-bulk'],
        ],
    )
    def test_constructor_subscription_path(self, priority, queue, mock_pubsub_v1):
        settings.TASKHAWK_QUEUE = 'myqueue'
        gcp_consumer = gcp.GooglePubSubConsumerBackend(priority=priority)
        assert gcp_consumer._subscription_path == f'projects/DUMMY_PROJECT_ID/subscriptions/{queue}'
        assert gcp_consumer._dlq_topic_path == f'projects/DUMMY_PROJECT_ID/topics/{queue}-dlq'

    def test_constructor(self, mock_pubsub_v1):
        gcp_consumer = gcp.GooglePubSubConsumerBackend(priority=Priority.default)
        assert gcp_consumer.subscriber == mock_pubsub_v1.SubscriberClient()
        assert gcp_consumer.publisher == mock_pubsub_v1.PublisherClient()

    @staticmethod
    def _build_gcp_received_message(message):
        queue_message = mock.create_autospec(ReceivedMessage)
        queue_message.ack_id = "dummy_ack_id"
        queue_message.message = mock.create_autospec(PubsubMessage)
        queue_message.message.message_id = str(time())
        queue_message.message.data = json.dumps(message.as_dict()).encode()
        queue_message.message.attributes = message.as_dict()['headers']
        queue_message.message.publish_time = arrow.utcnow().datetime
        queue_message.delivery_attempt = 1
        return queue_message

    def test_pull_messages(self, mock_pubsub_v1, gcp_consumer, gcp_settings):
        num_messages = 1
        visibility_timeout = 10

        gcp_consumer.pull_messages(num_messages, visibility_timeout)

        gcp_consumer.subscriber.pull.assert_called_once_with(
            subscription=gcp_consumer._subscription_path,
            max_messages=num_messages,
            retry=None,
            timeout=gcp_settings.GOOGLE_PUBSUB_READ_TIMEOUT_S,
        )

    def test_pull_messages_service_unavailable(self, mock_pubsub_v1, gcp_consumer, gcp_settings):
        num_messages = 1
        visibility_timeout = 10

        gcp_consumer.subscriber.pull = mock.MagicMock(side_effect=ServiceUnavailable("foobar"))
        results = gcp_consumer.pull_messages(num_messages, visibility_timeout)

        assert results == []
        gcp_consumer.subscriber.pull.assert_called_once_with(
            subscription=gcp_consumer._subscription_path,
            max_messages=num_messages,
            retry=None,
            timeout=gcp_settings.GOOGLE_PUBSUB_READ_TIMEOUT_S,
        )

    def test_success_extend_visibility_timeout(self, mock_pubsub_v1, gcp_consumer):
        visibility_timeout_s = 10
        ack_id = "dummy_ack_id"
        publish_time = arrow.utcnow().datetime
        delivery_attempt = 1

        gcp_consumer.extend_visibility_timeout(
            visibility_timeout_s, GoogleMetadata(ack_id, publish_time, delivery_attempt)
        )

        gcp_consumer.subscriber.modify_ack_deadline.assert_called_once_with(
            subscription=gcp_consumer._subscription_path, ack_ids=[ack_id], ack_deadline_seconds=visibility_timeout_s
        )

    @pytest.mark.parametrize("visibility_timeout", [-1, 601])
    def test_failure_extend_visibility_timeout(self, visibility_timeout, mock_pubsub_v1, gcp_consumer):
        publish_time = arrow.utcnow().datetime
        delivery_attempt = 1

        with pytest.raises(ValueError):
            gcp_consumer.extend_visibility_timeout(
                visibility_timeout, GoogleMetadata('dummy_ack_id', publish_time, delivery_attempt)
            )

        gcp_consumer.subscriber.subscription_path.assert_not_called()
        gcp_consumer.subscriber.modify_ack_deadline.assert_not_called()

    def test_success_requeue_dead_letter(self, mock_pubsub_v1, message):
        gcp_consumer = gcp.GooglePubSubConsumerBackend(priority=Priority.default, dlq=True)

        num_messages = 1
        visibility_timeout = 4

        queue_message = self._build_gcp_received_message(message)
        gcp_consumer.pull_messages = mock.MagicMock(side_effect=iter([[queue_message], None]))

        gcp_consumer.requeue_dead_letter(num_messages=num_messages, visibility_timeout=visibility_timeout)

        gcp_consumer.subscriber.modify_ack_deadline.assert_called_once_with(
            subscription=gcp_consumer._subscription_path,
            ack_ids=[queue_message.ack_id],
            ack_deadline_seconds=visibility_timeout,
        )
        gcp_consumer.pull_messages.assert_has_calls(
            [
                mock.call(num_messages=num_messages, visibility_timeout=visibility_timeout),
                mock.call(num_messages=num_messages, visibility_timeout=visibility_timeout),
            ]
        )
        gcp_consumer._publisher.publish.assert_called_once_with(
            gcp_consumer._dlq_topic_path[: -len("-dlq")], data=queue_message.message.data, **message.headers
        )
        gcp_consumer.subscriber.acknowledge.assert_called_once_with(
            subscription=gcp_consumer._subscription_path, ack_ids=[queue_message.ack_id]
        )

    def test_fetch_and_process_messages_success(self, mock_pubsub_v1, gcp_settings, message, gcp_consumer, reset_mocks):
        gcp_settings.TASKHAWK_PRE_PROCESS_HOOK = 'tests.test_backends.test_gcp.pre_process_hook'
        gcp_settings.TASKHAWK_POST_PROCESS_HOOK = 'tests.test_backends.test_gcp.post_process_hook'
        num_messages = 3
        visibility_timeout = 4

        queue_message = self._build_gcp_received_message(message)
        received_messages = mock.MagicMock()
        received_messages.received_messages = [queue_message]
        gcp_consumer.subscriber.pull = mock.MagicMock(return_value=received_messages)
        gcp_consumer.process_message = mock.MagicMock(wraps=gcp_consumer.process_message)
        gcp_consumer.message_handler = mock.MagicMock(wraps=gcp_consumer.message_handler)

        gcp_consumer.fetch_and_process_messages(num_messages, visibility_timeout)

        gcp_consumer.subscriber.pull.assert_called_once_with(
            subscription=gcp_consumer._subscription_path,
            max_messages=num_messages,
            retry=None,
            timeout=gcp_settings.GOOGLE_PUBSUB_READ_TIMEOUT_S,
        )
        gcp_consumer.process_message.assert_called_once_with(queue_message)
        gcp_consumer.message_handler.assert_called_once_with(
            queue_message.message.data.decode(),
            GoogleMetadata(queue_message.ack_id, queue_message.message.publish_time, queue_message.delivery_attempt),
        )
        gcp_consumer.subscriber.acknowledge.assert_called_once_with(
            subscription=gcp_consumer._subscription_path, ack_ids=[queue_message.ack_id]
        )
        pre_process_hook.assert_called_once_with(google_pubsub_message=queue_message)
        post_process_hook.assert_called_once_with(google_pubsub_message=queue_message)

    def test_error_count_increments(self, mock_pubsub_v1, gcp_settings, gcp_consumer):
        assert gcp_consumer.error_count == 0

        gcp_consumer.subscriber.pull.side_effect = ServiceUnavailable("Service Unavailable")

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 1

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 2

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 3

        gcp_consumer.subscriber.pull.assert_has_calls(
            [
                mock.call(
                    subscription=gcp_consumer._subscription_path,
                    max_messages=1,
                    retry=None,
                    timeout=gcp_settings.GOOGLE_PUBSUB_READ_TIMEOUT_S,
                )
                for _ in range(3)
            ]
        )

    def test_error_count_resets(self, mock_pubsub_v1, gcp_settings, gcp_consumer):
        gcp_consumer.subscriber.pull.side_effect = ServiceUnavailable("Service Unavailable")

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 1

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 2

        gcp_consumer.subscriber.pull.side_effect = None

        gcp_consumer.pull_messages(num_messages=1)
        assert gcp_consumer.error_count == 0

        gcp_consumer.subscriber.pull.assert_has_calls(
            [
                mock.call(
                    subscription=gcp_consumer._subscription_path,
                    max_messages=1,
                    retry=None,
                    timeout=gcp_settings.GOOGLE_PUBSUB_READ_TIMEOUT_S,
                )
                for _ in range(3)
            ]
        )
