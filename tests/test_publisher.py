import copy
from decimal import Decimal
import json
from unittest import mock
import uuid

import pytest

from taskhawk import Priority
from taskhawk.conf import settings
from taskhawk.models import Message
from taskhawk.publisher import publish, _get_sns_topic, _convert_to_json, _publish_over_sns, _publish_over_sqs


@pytest.mark.parametrize(
    'priority,suffix',
    [
        (Priority.default, ''),
        (Priority.low, '-low-priority'),
        (Priority.high, '-high-priority'),
        (Priority.bulk, '-bulk'),
    ],
)
def test__get_sns_topic(priority, suffix):
    assert _get_sns_topic(priority) == f'arn:aws:sns:{settings.AWS_REGION}:{settings.AWS_ACCOUNT_ID}:taskhawk-' \
                                       f'{settings.TASKHAWK_QUEUE.lower()}{suffix}'


@mock.patch('taskhawk.publisher._get_sns_client', autospec=True)
def test__publish_over_sns(mock_get_sns_client, message):
    priority = Priority.high
    topic = _get_sns_topic(priority)
    message_json = _convert_to_json(message.as_dict())

    _publish_over_sns(topic, message_json, message.headers)

    mock_get_sns_client.assert_called_once_with()
    mock_get_sns_client.return_value.publish.assert_called_once_with(
        TopicArn=topic,
        Message=message_json,
        MessageAttributes={
            k: {
                'DataType': 'String',
                'StringValue': str(v),
            } for k, v in message.headers.items()
        },
    )


def test__publish_over_sqs(message):
    message_json = _convert_to_json(message.as_dict())
    queue = mock.MagicMock()

    _publish_over_sqs(queue, message_json, message.headers)

    queue.send_message.assert_called_once_with(
        MessageBody=message_json,
        MessageAttributes={
            k: {
                'DataType': 'String',
                'StringValue': str(v),
            } for k, v in message.headers.items()
        },
    )


@pytest.fixture(name='message_with_decimal')
def _message_with_decimal(message_data):
    message_data = copy.deepcopy(message_data)
    message_data['args'][0] = Decimal(1469056316326)
    return Message(message_data)


def test__convert_to_json_decimal(message_with_decimal):
    assert json.loads(_convert_to_json(message_with_decimal.as_dict()))['args'][0] == \
        float(message_with_decimal.args[0])


@mock.patch('taskhawk.publisher.get_queue_name', autospec=True)
@mock.patch('taskhawk.publisher.get_queue', autospec=True)
@mock.patch('taskhawk.publisher._convert_to_json', autospec=True)
@mock.patch('taskhawk.publisher._publish_over_sqs', autospec=True)
def test_publish_non_lambda(mock_publish_over_sqs, mock_convert_to_json, mock_get_queue, mock_get_queue_name, message):
    assert settings.TASKHAWK_QUEUE
    sqs_id = str(uuid.uuid4())
    message.priority = Priority.high
    mock_publish_over_sqs.return_value = {'MessageId': sqs_id}

    publish(message)

    mock_get_queue_name.assert_called_once_with(message.priority)
    mock_get_queue.assert_called_once_with(mock_get_queue_name.return_value)
    mock_publish_over_sqs.assert_called_once_with(
        mock_get_queue.return_value,
        mock_convert_to_json.return_value,
        message.headers
    )
    mock_convert_to_json.assert_called_once_with(message.as_dict())


@mock.patch('taskhawk.publisher._convert_to_json', autospec=True)
@mock.patch('taskhawk.publisher._publish_over_sns', autospec=True)
def test_publish_lambda(mock_publish_over_sns, mock_convert_to_json, message, settings):
    settings.IS_LAMBDA_APP = True

    sns_id = str(uuid.uuid4())
    message.priority = Priority.high
    mock_publish_over_sns.return_value = {'MessageId': sns_id}

    publish(message)

    topic = _get_sns_topic(message.priority)
    mock_publish_over_sns.assert_called_once_with(
        topic,
        mock_convert_to_json.return_value,
        message.headers
    )
    mock_convert_to_json.assert_called_once_with(message.as_dict())
