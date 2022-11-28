import itertools
import threading
from typing import Optional

from taskhawk.backends.utils import get_consumer_backend
from taskhawk.models import Priority


def process_messages_for_lambda_consumer(lambda_event: dict) -> None:
    """
    Process messages for a Taskhawk consumer Lambda app, and calls the task function with given `args` and `kwargs`

    If the task function accepts a param called `metadata`, it'll be passed in with a dict containing the metadata
    fields: id, timestamp, version, receipt.

    In case of an exception, the message is kept on Lambda's retry queue and processed again a fixed number of times.
    If the task function keeps failing, Lambda dead letter queue mechanism kicks in and the message is moved to the
    dead-letter queue.
    """
    sns_consumer_backend = get_consumer_backend()
    sns_consumer_backend.process_messages(lambda_event)


def listen_for_messages(
    priority: Priority,
    num_messages: int = 1,
    visibility_timeout_s: Optional[int] = None,
    loop_count: Optional[int] = None,
    shutdown_event: Optional[threading.Event] = None,
) -> None:
    """
    Starts a Taskhawk listener for message types provided and calls the task function with given `args` and `kwargs`.

    If the task function accepts a param called `metadata`, it'll be passed in with a dict containing the metadata
    fields: id, timestamp, version, receipt.

    The message is explicitly deleted only if task function ran successfully. In case of an exception the message is
    kept on queue and processed again. If the task function keeps failing, SQS dead letter queue mechanism kicks in and
    the message is moved to the dead-letter queue.

    This function is blocking by default. It may be run for specific number of loops by passing `loop_count`. It may
    also be stopped by passing a shut down event object which can be set to stop the function.

    :param priority: The priority queue to listen to
    :param num_messages: Maximum number of messages to fetch in one SQS API call. Defaults to 1
    :param visibility_timeout_s: The number of seconds the message should remain invisible to other queue readers.
        Defaults to None, which is queue default
    :param loop_count: How many times to fetch messages from SQS. Default to None, which means loop forever.
    :param shutdown_event: An event to signal that the process should shut down. This prevents more messages from
        being de-queued and function exits after the current messages have been processed.
    """
    if not shutdown_event:
        shutdown_event = threading.Event()

    consumer_backend = get_consumer_backend(priority=priority)
    for count in itertools.count():
        if (loop_count is None or count < loop_count) and not shutdown_event.is_set():
            consumer_backend.fetch_and_process_messages(
                num_messages=num_messages, visibility_timeout=visibility_timeout_s
            )
        else:
            break
