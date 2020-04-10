import json
import math
from decimal import Decimal
from unittest import mock

import pytest

from taskhawk.backends.base import TaskhawkBaseBackend, TaskhawkConsumerBaseBackend, TaskhawkPublisherBaseBackend
from taskhawk.models import Message, ValidationError, Priority
from taskhawk.exceptions import LoggingException, RetryException, IgnoreException
from taskhawk.backends import base
from taskhawk.backends.utils import get_consumer_backend, get_publisher_backend


class MockBackend(TaskhawkConsumerBaseBackend, TaskhawkPublisherBaseBackend):
    def __init__(self, priority: Priority):
        self.priority = priority


class TestBackends:
    def test_success_get_consumer_backend(self, settings):
        settings.TASKHAWK_CONSUMER_BACKEND = "tests.test_backends.test_base.MockBackend"

        consumer_backend = get_consumer_backend(Priority.default)

        assert isinstance(consumer_backend, MockBackend)

    def test_success_get_publisher_backend(self, settings):
        settings.TASKHAWK_PUBLISHER_BACKEND = "tests.test_backends.test_base.MockBackend"

        publisher_backend = get_publisher_backend(Priority.default)

        assert isinstance(publisher_backend, MockBackend)

    @pytest.mark.parametrize("get_backend_fn", [get_publisher_backend, get_consumer_backend])
    def test_failure(self, get_backend_fn, settings):
        settings.TASKHAWK_PUBLISHER_BACKEND = settings.TASKHAWK_CONSUMER_BACKEND = "taskhawk.backends.Invalid"

        with pytest.raises(ImportError):
            get_backend_fn()


@mock.patch('taskhawk.backends.base.Message.call_task', autospec=True)
class TestMessageHandler:
    def test_success(self, mock_call_task, message_data, message, consumer_backend):
        provider_metadata = mock.Mock()
        consumer_backend.message_handler(json.dumps(message_data), provider_metadata)
        mock_call_task.assert_called_once_with(message)

    def test_fails_on_invalid_json(self, mock_call_task, consumer_backend):
        with pytest.raises(ValueError):
            consumer_backend.message_handler("bad json", None)

    @mock.patch('taskhawk.backends.base.Message.validate', autospec=True)
    def test_fails_on_validation_error(self, mock_validate, mock_call_task, message_data, consumer_backend):
        error_message = 'Invalid message body'
        mock_validate.side_effect = ValidationError(error_message)
        with pytest.raises(ValidationError):
            consumer_backend.message_handler(json.dumps(message_data), None)
        mock_call_task.assert_not_called()

    def test_fails_on_task_failure(self, mock_call_task, message_data, message, consumer_backend):
        mock_call_task.side_effect = Exception
        with pytest.raises(mock_call_task.side_effect):
            consumer_backend.message_handler(json.dumps(message_data), None)


pre_process_hook = mock.MagicMock()
post_process_hook = mock.MagicMock()


class TestFetchAndProcessMessages:
    def test_success(self, consumer_backend):
        num_messages = 3
        visibility_timeout = 4

        consumer_backend.pull_messages = mock.MagicMock()
        consumer_backend.pull_messages.return_value = [mock.MagicMock(), mock.MagicMock()]
        consumer_backend.process_message = mock.MagicMock()
        consumer_backend.delete_message = mock.MagicMock()

        consumer_backend.fetch_and_process_messages(num_messages, visibility_timeout)

        consumer_backend.pull_messages.assert_called_once_with(num_messages, visibility_timeout)
        consumer_backend.process_message.assert_has_calls(
            [mock.call(x) for x in consumer_backend.pull_messages.return_value]
        )
        consumer_backend.delete_message.assert_has_calls(
            [mock.call(x) for x in consumer_backend.pull_messages.return_value]
        )

    def test_preserves_messages(self, consumer_backend):
        consumer_backend.pull_messages = mock.MagicMock()
        consumer_backend.pull_messages.return_value = [mock.MagicMock()]
        consumer_backend.process_message = mock.MagicMock()
        consumer_backend.process_message.side_effect = Exception

        consumer_backend.fetch_and_process_messages()

        consumer_backend.pull_messages.return_value[0].delete.assert_not_called()

    def test_ignore_delete_error(self, consumer_backend):
        queue_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[queue_message])
        consumer_backend.process_message = mock.MagicMock()
        consumer_backend.delete_message = mock.MagicMock(side_effect=Exception)

        with mock.patch.object(base.logger, 'exception') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once()

        consumer_backend.delete_message.assert_called_once_with(consumer_backend.pull_messages.return_value[0])

    def test_pre_process_hook(self, consumer_backend, settings):
        pre_process_hook.reset_mock()
        settings.TASKHAWK_PRE_PROCESS_HOOK = 'tests.test_backends.test_base.pre_process_hook'
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock.MagicMock(), mock.MagicMock()])

        consumer_backend.fetch_and_process_messages()

        pre_process_hook.assert_has_calls(
            [
                mock.call(**consumer_backend.pre_process_hook_kwargs(x))
                for x in consumer_backend.pull_messages.return_value
            ]
        )

    def test_pre_process_hook_exception(self, consumer_backend, settings):
        pre_process_hook.reset_mock()
        pre_process_hook.side_effect = RuntimeError('fail')
        mock_message = mock.MagicMock()
        settings.TASKHAWK_PRE_PROCESS_HOOK = 'tests.test_backends.test_base.pre_process_hook'
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock_message])

        with mock.patch.object(base.logger, 'exception') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once_with(
                'Exception in post process hook for message', extra={'queue_message': mock_message}
            )

        pre_process_hook.assert_called_once_with(**consumer_backend.pre_process_hook_kwargs(mock_message))
        mock_message.delete.assert_not_called()

    def test_post_process_hook(self, consumer_backend, settings):
        post_process_hook.reset_mock()
        settings.TASKHAWK_POST_PROCESS_HOOK = 'tests.test_backends.test_base.post_process_hook'
        consumer_backend.process_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock.MagicMock(), mock.MagicMock()])

        consumer_backend.fetch_and_process_messages()

        post_process_hook.assert_has_calls(
            [
                mock.call(**consumer_backend.post_process_hook_kwargs(x))
                for x in consumer_backend.pull_messages.return_value
            ]
        )

    def test_post_process_hook_exception(self, consumer_backend, settings):
        settings.TASKHAWK_POST_PROCESS_HOOK = 'tests.test_backends.test_base.post_process_hook'
        consumer_backend.process_message = mock.MagicMock()
        mock_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock_message])
        post_process_hook.reset_mock()
        post_process_hook.side_effect = RuntimeError('fail')

        with mock.patch.object(base.logger, 'exception') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once_with(
                'Exception in post process hook for message', extra={'queue_message': mock_message}
            )

        post_process_hook.assert_called_once_with(**consumer_backend.pre_process_hook_kwargs(mock_message))
        mock_message.delete.assert_not_called()

    def test_special_handling_logging_error(self, consumer_backend):
        mock_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock_message])
        consumer_backend.process_message = mock.MagicMock(
            side_effect=LoggingException('foo', extra={'mickey': 'mouse'})
        )

        with mock.patch.object(base.logger, 'exception') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once_with('foo', extra={'mickey': 'mouse'})

    def test_special_handling_retry_error(self, consumer_backend):
        mock_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock_message])
        consumer_backend.process_message = mock.MagicMock(side_effect=RetryException)

        with mock.patch.object(base.logger, 'info') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once()

    def test_special_handling_ignore_exception(self, consumer_backend):
        mock_message = mock.MagicMock()
        consumer_backend.pull_messages = mock.MagicMock(return_value=[mock_message])
        consumer_backend.process_message = mock.MagicMock(side_effect=IgnoreException)

        with mock.patch.object(base.logger, 'info') as logging_mock:
            consumer_backend.fetch_and_process_messages()

            logging_mock.assert_called_once()


@pytest.mark.parametrize('value', [1469056316326, 1469056316326.123])
def test__convert_to_json_decimal(value, message_data):
    backend = TaskhawkBaseBackend()
    message_data['args'][0] = Decimal(value)
    message = Message(message_data)
    assert json.loads(backend.message_payload(message.as_dict()))['args'][0] == float(message.args[0])


@pytest.mark.parametrize('value', [math.nan, math.inf, -math.inf])
def test__convert_to_json_disallow_nan(value, message_data):
    backend = TaskhawkBaseBackend()
    message_data['args'][0] = value
    message = Message(message_data)
    with pytest.raises(ValueError):
        backend.message_payload(message.as_dict())


def test__convert_to_json_non_serializable(message_data):
    backend = TaskhawkBaseBackend()
    message_data['args'][0] = object()
    message = Message(message_data)
    with pytest.raises(TypeError):
        backend.message_payload(message.as_dict())


class TestPublisher:
    def test_publish(self, message, mock_publisher_backend):
        message.validate()

        mock_publisher_backend.publish(message)

        payload = json.dumps(message.as_dict())

        mock_publisher_backend._publish.assert_called_once_with(message, payload, message.headers)
