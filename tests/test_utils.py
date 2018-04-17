import random
from unittest import mock
import uuid

from taskhawk.models import Priority
from taskhawk.utils import extend_visibility_timeout


@mock.patch('taskhawk.utils._get_sqs_client')
@mock.patch('taskhawk.utils.get_queue_name')
def test_extend_visibility_timeout(mock_get_queue_name, mock_get_sqs_client):
    priority = Priority.high
    receipt = str(uuid.uuid4())
    visibility_timeout_s = random.randint(0, 1000)

    extend_visibility_timeout(priority, receipt, visibility_timeout_s)

    mock_get_queue_name.assert_called_once_with(priority)
    mock_get_sqs_client.assert_called_once_with()
    mock_get_sqs_client.return_value.get_queue_url.assert_called_once_with(
        QueueName=mock_get_queue_name.return_value
    )
    mock_get_sqs_client.return_value.change_message_visibility.assert_called_once_with(
        QueueUrl=mock_get_sqs_client.return_value.get_queue_url.return_value['QueueUrl'],
        ReceiptHandle=receipt,
        VisibilityTimeout=visibility_timeout_s,
    )
