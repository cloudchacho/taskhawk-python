import random
import time
from unittest import mock

import funcy
import pytest

from taskhawk.exceptions import ValidationError, TaskNotFound
from taskhawk.models import Message, Priority, Metadata
from .tasks import send_email


class TestMetadata:
    def test_new(self, message_data):
        metadata = Metadata(message_data)
        assert metadata.timestamp == message_data['metadata']['timestamp']
        assert metadata.headers == message_data['headers']
        assert metadata.id == message_data['id']
        assert metadata.version == message_data['metadata']['version']
        assert metadata.priority == Priority[message_data['metadata']['priority']]
        assert metadata.provider_metadata is None

    def test_as_dict(self, message_data):
        metadata = Metadata(message_data)
        assert metadata.as_dict() == {
            'priority': metadata.priority.name,
            'timestamp': metadata.timestamp,
            'version': metadata.version,
        }

    def test_equal(self, message_data):
        assert Metadata(message_data) == Metadata(message_data)

    def test_equal_fail(self, message_data):
        metadata = Metadata(message_data)
        message_data['id'] = "foobar"
        metadata2 = Metadata(message_data)
        assert metadata != metadata2

    @mock.patch('taskhawk.models.get_consumer_backend', autospec=True)
    def test_extend_visibility_timeout(self, mock_get_consumer_backend, message_data):
        visibility_timeout_s = random.randint(0, 1000)

        metadata = Metadata(message_data)
        metadata.provider_metadata = object()

        metadata.extend_visibility_timeout(visibility_timeout_s)

        mock_get_consumer_backend.assert_called_once_with(priority=metadata.priority)
        mock_get_consumer_backend.return_value.extend_visibility_timeout.assert_called_once_with(
            visibility_timeout_s, metadata.provider_metadata
        )


class TestMessageMethods:
    publisher = 'myapi'

    @mock.patch('taskhawk.models.time.time', autospec=True)
    def test_create_metadata(self, mock_time):
        mock_time.return_value = time.time()

        assert Message._create_metadata(Priority.high) == {
            'priority': Priority.high.name,
            'timestamp': int(mock_time.return_value * 1000),
            'version': Message.CURRENT_VERSION,
        }

    def test_new(self, message_data):
        message = Message.new(
            message_data['task'],
            Priority[message_data['metadata']['priority']],
            message_data['args'],
            message_data['kwargs'],
            message_data['id'],
            message_data['headers'],
        )

        assert message.id == message_data['id']
        assert message.headers == message_data['headers']
        assert message.task_name == message_data['task']
        assert message.args == message_data['args']
        assert message.kwargs == message_data['kwargs']
        assert message.priority == Priority[message_data['metadata']['priority']]

    def test_as_dict(self, message):
        assert message.as_dict() == {
            'id': message.id,
            'metadata': message.metadata.as_dict(),
            'headers': message.headers,
            'task': message.task_name,
            'args': message.args,
            'kwargs': message.kwargs,
        }

    def test_validate_looks_up_task(self, message):
        message.validate()
        assert message.task == send_email.task

    def test_validate_str_timestamp(self, message_data):
        message_data['metadata']['timestamp'] = '2015-11-11T21:29:54Z'

        Message(message_data).validate()

    def test_validate_bad_timestamp(self, message_data):
        message_data['metadata']['timestamp'] = 'foobar'

        with pytest.raises(ValidationError):
            Message(message_data)

    @pytest.mark.parametrize(
        'missing_data',
        ['id', 'metadata', 'metadata__version', 'metadata__timestamp', 'headers', 'task', 'args', 'kwargs'],
    )
    @pytest.mark.parametrize('is_none', [True, False])
    def test_validate_missing_data(self, missing_data, is_none, message_data):
        if missing_data.startswith('metadata__'):
            if is_none:
                message_data['metadata'][missing_data.split('__')[1]] = None
            else:
                del message_data['metadata'][missing_data.split('__')[1]]
        else:
            if is_none:
                message_data[missing_data] = None
            else:
                del message_data[missing_data]

        with pytest.raises(ValidationError):
            Message(message_data).validate()

    def test_validate_invalid_version(self, message_data):
        message_data['metadata']['version'] = '2.0'

        with pytest.raises(ValidationError):
            Message(message_data).validate()

    @mock.patch('taskhawk.task_manager.Task.find_by_name', side_effect=TaskNotFound)
    def test_validate_missing_task(self, _, message_data):
        with pytest.raises(ValidationError):
            Message(message_data).validate()

    @mock.patch('tests.tasks._send_email', autospec=True)
    def test_call_task(self, mock_send_email, message):
        message.validate()
        message.call_task()
        mock_send_email.assert_called_once()
        assert mock_send_email.call_args[0] == tuple(message.args)
        assert funcy.project(mock_send_email.call_args[1], message.kwargs.keys()) == message.kwargs
        assert mock_send_email.call_args[1]['headers'] == message.headers
        assert mock_send_email.call_args[1]['metadata'] == Metadata(message.as_dict())

    def test_equal(self, message):
        assert message == message

    def test_equal_fail(self, message):
        assert message != message.as_dict()

    def test_items(self, message):
        assert dict(message.items()) == message.as_dict()
