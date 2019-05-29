from unittest import mock

from taskhawk.commands import requeue_dead_letter
from taskhawk.models import Priority


@mock.patch('taskhawk.commands.get_consumer_backend', autospec=True)
def test_requeue_dead_letter(mock_get_consumer_backend):
    requeue_dead_letter(priority=Priority.default)
    mock_get_consumer_backend.assert_called_once_with(priority=Priority.default, dlq=True)
    mock_get_consumer_backend.return_value.requeue_dead_letter.assert_called_once_with(10, None)
