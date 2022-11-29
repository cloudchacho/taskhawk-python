import logging
import time
import uuid
from contextlib import contextmanager
from unittest import mock

import pytest

# initialize tasks
import tests.tasks  # noqa
import taskhawk.conf
from taskhawk.backends.base import TaskhawkBaseBackend, TaskhawkPublisherBaseBackend
from taskhawk.backends.utils import get_publisher_backend, get_consumer_backend
from taskhawk.models import Priority, Message


try:
    # may not be available
    from moto import mock_sqs, mock_sns
except ImportError:
    pass


def pytest_configure():
    logging.basicConfig()


@pytest.fixture
def settings():
    """
    Use this fixture to override settings. Changes are automatically reverted
    """
    original_module = taskhawk.conf.settings._user_settings

    class Wrapped:
        # default to the original module, but allow tests to setattr which would override
        def __getattr__(self, name):
            return getattr(original_module, name)

    taskhawk.conf.settings._user_settings = Wrapped()
    taskhawk.conf.settings.clear_cache()

    # since consumer/publisher settings may have changed
    get_publisher_backend.cache_clear()
    get_consumer_backend.cache_clear()

    try:
        yield taskhawk.conf.settings._user_settings
    finally:
        taskhawk.conf.settings._user_settings = original_module
        taskhawk.conf.settings.clear_cache()

        # since consumer/publisher settings may have changed
        get_publisher_backend.cache_clear()
        get_consumer_backend.cache_clear()


@pytest.fixture(name='message_data')
def _message_data():
    return {
        "id": "b1328174-a21c-43d3-b303-964dfcc76efc",
        "metadata": {"timestamp": int(time.time() * 1000), "version": "1.0", "priority": "default"},
        "headers": {'request_id': str(uuid.uuid4())},
        "task": "tests.tasks.send_email",
        "args": ["example@email.com", "Hello!"],
        "kwargs": {"from_email": "hello@spammer.com"},
    }


@pytest.fixture()
def message(message_data):
    return Message(message_data)


@contextmanager
def _mock_boto3():
    settings.AWS_REGION = 'us-west-1'
    with mock_sqs(), mock_sns(), mock.patch("taskhawk.backends.aws.boto3", autospec=True) as boto3_mock:
        yield boto3_mock


@pytest.fixture
def mock_boto3():
    with _mock_boto3() as m:
        yield m


@pytest.fixture()
def sqs_consumer_backend(mock_boto3):
    # may not be available
    from taskhawk.backends import aws

    yield aws.AWSSQSConsumerBackend(priority=Priority.default)


@pytest.fixture
def mock_pubsub_v1():
    # may not be available
    from google.cloud import pubsub_v1

    with mock.patch("taskhawk.backends.gcp.pubsub_v1", autospec=True) as pubsub_v1_mock:
        pubsub_v1_mock.SubscriberClient.subscription_path = pubsub_v1.SubscriberClient.subscription_path
        pubsub_v1_mock.PublisherClient.topic_path = pubsub_v1.PublisherClient.topic_path
        yield pubsub_v1_mock


@pytest.fixture(params=['aws', 'google'])
def consumer_backend(request):
    if request.param == 'aws':
        try:
            import taskhawk.backends.aws  # noqa

            with _mock_boto3():
                yield TaskhawkBaseBackend.build(
                    "taskhawk.backends.aws.AWSSQSConsumerBackend", priority=Priority.default
                )
        except ImportError:
            pytest.skip("AWS backend not importable")

    if request.param == 'google':
        try:
            import taskhawk.backends.gcp  # noqa

            with mock.patch("taskhawk.backends.gcp.pubsub_v1"), mock.patch(
                "taskhawk.backends.gcp.google_auth_default", return_value=(None, "DUMMY")
            ):
                yield TaskhawkBaseBackend.build(
                    "taskhawk.backends.gcp.GooglePubSubConsumerBackend", priority=Priority.default
                )
        except ImportError:
            pytest.skip("Google backend not importable")


@pytest.fixture(
    params=["taskhawk.backends.aws.AWSSNSConsumerBackend", "taskhawk.backends.gcp.GooglePubSubPublisherBackend"]
)
def publisher_backend(request, mock_boto3):
    with mock.patch("taskhawk.backends.gcp.pubsub_v1"):
        yield TaskhawkBaseBackend.build(request.param, priority=Priority.default)


@pytest.fixture()
def mock_publisher_backend():
    with mock.patch.object(TaskhawkPublisherBaseBackend, '_publish'):
        yield TaskhawkPublisherBaseBackend()
