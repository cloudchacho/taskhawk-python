from typing import Optional

from taskhawk.backends.utils import get_consumer_backend
from taskhawk.models import Priority


def requeue_dead_letter(
    priority: Priority, num_messages: Optional[int] = 10, visibility_timeout: Optional[int] = None
) -> None:
    """
    Re-queues everything in the Taskhawk DLQ back into the Taskhawk queue.

    :param priority: The priority queue to listen to
    :param num_messages: Maximum number of messages to fetch in one SQS call. Defaults to 10.
    :param visibility_timeout: The number of seconds the message should remain invisible to other queue readers.
        Defaults to None, which is queue default
    """
    consumer_backend = get_consumer_backend(priority=priority, dlq=True)
    consumer_backend.requeue_dead_letter(num_messages, visibility_timeout)
