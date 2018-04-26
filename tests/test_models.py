import time
from unittest import mock
import uuid

import funcy
import pytest

from taskhawk import ValidationError, TaskNotFound, Priority
from taskhawk.models import Message
from .tasks import send_email


class TestMessageMethods:
    publisher = 'myapi'

    @mock.patch('taskhawk.models.time.time', autospec=True)
    def test_create_metadata(self, mock_time):
        mock_time.return_value = time.time()

        assert Message._create_metadata() == {
            'priority': Priority.default.name,
            'timestamp': int(mock_time.return_value * 1000),
            'version': Message.CURRENT_VERSION,
        }

    def test_new(self, message_data):
        message = Message.new(
            message_data['task'], message_data['args'], message_data['kwargs'], message_data['id'],
            message_data['headers'],
        )

        assert message.id == message_data['id']
        assert message.headers == message_data['headers']
        assert message.task_name == message_data['task']
        assert message.args == message_data['args']
        assert message.kwargs == message_data['kwargs']

    def test_as_dict(self, message):
        assert message.as_dict() == {
            'id': message.id,
            'metadata': message.metadata,
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

    @pytest.mark.parametrize('missing_data', ['id', 'metadata', 'metadata__version', 'metadata__timestamp',
                                              'headers', 'task', 'args', 'kwargs'])
    def test_validate_missing_data(self, missing_data, message_data):
        if missing_data.startswith('metadata__'):
            message_data['metadata'][missing_data.split('__')[1]] = None
        else:
            message_data[missing_data] = None

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
        receipt = str(uuid.uuid4())
        message.validate()
        message.call_task(receipt)
        mock_send_email.assert_called_once()
        assert mock_send_email.call_args[0] == tuple(message.args)
        assert funcy.project(mock_send_email.call_args[1], message.kwargs.keys()) == message.kwargs
        assert mock_send_email.call_args[1]['headers'] == message.headers
        assert mock_send_email.call_args[1]['metadata'] == {
            'id': message.id,
            'timestamp': message.timestamp,
            'version': message.version,
            'receipt': receipt,
            'priority': Priority.default,
        }
