from unittest import mock

from taskhawk.publisher import publish


@mock.patch('taskhawk.publisher.get_publisher_backend', autospec=True)
def test_publish(mock_get_publisher_backend, message):
    publish(message)

    mock_get_publisher_backend.assert_called_once_with(priority=message.priority)
    mock_get_publisher_backend.return_value.publish.assert_called_once_with(message)
