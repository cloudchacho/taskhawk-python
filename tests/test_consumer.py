from unittest import mock

from taskhawk.consumer import process_messages_for_lambda_consumer, listen_for_messages
from taskhawk.models import Priority


@mock.patch('taskhawk.consumer.get_consumer_backend', autospec=True)
def test_process_messages_for_lambda_consumer(mock_get_backend):
    event = mock.Mock()

    process_messages_for_lambda_consumer(event)

    mock_get_backend.assert_called_once_with()
    mock_get_backend.return_value.process_messages.assert_called_once_with(event)


@mock.patch('taskhawk.consumer.get_consumer_backend', autospec=True)
class TestListenForMessages:
    def test_listen_for_messages(self, mock_get_backend):
        num_messages = 3
        visibility_timeout_s = 4
        loop_count = 1
        priority = Priority.default

        listen_for_messages(priority, num_messages, visibility_timeout_s, loop_count)

        mock_get_backend.assert_called_once_with(priority=priority)
        mock_get_backend.return_value.fetch_and_process_messages.assert_called_once_with(
            num_messages=num_messages, visibility_timeout=visibility_timeout_s
        )
