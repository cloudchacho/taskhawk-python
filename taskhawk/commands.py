import json
import logging

import funcy

from taskhawk.conf import settings
from taskhawk.consumer import get_queue_name, get_queue, get_queue_messages
from taskhawk import Priority


class PartialFailure(Exception):
    """
    Error indicating either send_messages or delete_messages API call failed partially
    """
    def __init__(self, result, *args):
        self.success_count = len(result['Successful'])
        self.failure_count = len(result['Failed'])
        self.result = result
        super().__init__(*args)


def _enqueue_messages(queue, queue_messages, delay_seconds: int=None) -> None:
    params = {}

    if delay_seconds:
        assert isinstance(delay_seconds, int)
        params["DelaySeconds"] = delay_seconds

    result = queue.send_messages(
        Entries=[
            funcy.merge(
                {
                    'Id': queue_message.message_id,
                    'MessageBody': queue_message.body,
                },
                {
                    'MessageAttributes': queue_message.message_attributes
                } if queue_message.message_attributes else {},
                params
            )
            for queue_message in queue_messages
        ]
    )
    if result.get('Failed'):
        raise PartialFailure(result)


def get_dead_letter_queue(queue):
    queue_name = json.loads(queue.attributes['RedrivePolicy'])['deadLetterTargetArn'].split(':')[-1]
    return get_queue(queue_name)


def requeue_dead_letter(priority: Priority, num_messages: int=10, visibility_timeout: int=None) -> None:
    """
    Re-queues everything in the Taskhawk DLQ back into the Taskhawk queue.
    :param priority: The priority queue to listen to
    :param num_messages: Maximum number of messages to fetch in one SQS call. Defaults to 10.
    :param visibility_timeout: The number of seconds the message should remain invisible to other queue readers.
        Defaults to None, which is queue default
    """
    if settings.IS_LAMBDA_APP:
        logging.warning("Not supported for Lambda apps")
        return

    queue = get_queue(get_queue_name(priority))

    dead_letter_queue = get_dead_letter_queue(queue)

    logging.info("Re-queueing messages from {} to {}".format(dead_letter_queue.url, queue.url))
    while True:
        queue_messages = get_queue_messages(
            dead_letter_queue, num_messages=num_messages, visibility_timeout=visibility_timeout
        )
        if not queue_messages:
            break

        logging.info("got {} messages from dlq".format(len(queue_messages)))

        _enqueue_messages(queue, queue_messages)
        response = dead_letter_queue.delete_messages(
            Entries=[
                {
                    'Id': message.message_id,
                    'Receipt': message.receipt_handle
                }
                for message in queue_messages
            ]
        )
        if response['Failed']:
            raise PartialFailure(response)

        logging.info("Re-queued {} messages".format(len(queue_messages)))
