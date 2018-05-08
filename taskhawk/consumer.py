import json
import logging
import typing

import boto3
import boto3.resources.base
import boto3.resources.model

try:
    from django import db
except ImportError:
    db = None

from taskhawk.conf import settings
from taskhawk.exceptions import RetryException, LoggingException, ValidationError, IgnoreException
from taskhawk.models import Message
from taskhawk import Priority


WAIT_TIME_SECONDS = 20  # Maximum allowed by SQS

logger = logging.getLogger(__name__)


def _get_sqs_resource():
    return boto3.resource(
        'sqs',
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY,
        aws_secret_access_key=settings.AWS_SECRET_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        endpoint_url=settings.AWS_ENDPOINT_SQS,
    )


def get_queue(queue_name: str):
    sqs = _get_sqs_resource()
    return sqs.get_queue_by_name(QueueName=queue_name)


def log_received_message(message_body: dict) -> None:
    logger.debug('Received message', extra={
        'message_body': message_body,
    })


def log_invalid_message(message_json: str) -> None:
    logger.error('Received invalid message', extra={
        'message_json': message_json,
    })


def _load_and_validate_message(data: dict) -> Message:
    message = Message(data)
    message.validate()
    return message


def message_handler(message_json: str, receipt: typing.Optional[str]) -> None:
    try:
        message_body = json.loads(message_json)
        message = _load_and_validate_message(message_body)
    except (ValidationError, ValueError):
        log_invalid_message(message_json)
        raise

    log_received_message(message_body)

    try:
        message.call_task(receipt)
    except IgnoreException:
        logger.info(f'Ignoring task {message.id}')
        return
    except LoggingException as e:
        # log with message and extra
        logger.exception(str(e), extra=e.extra)
        # let it bubble up so message ends up in DLQ
        raise
    except RetryException:
        # Retry without logging exception
        logger.info('Retrying due to exception')
        # let it bubble up so message ends up in DLQ
        raise
    except Exception:
        logger.exception(f'Exception while processing message')
        # let it bubble up so message ends up in DLQ
        raise


def message_handler_sqs(queue_message) -> None:
    message_json = queue_message.body
    receipt = queue_message.receipt_handle

    message_handler(message_json, receipt)


def message_handler_lambda(lambda_record: dict) -> None:
    message_json = lambda_record['Sns']['Message']
    receipt = None

    message_handler(message_json, receipt)


def get_queue_messages(queue, num_messages: int, visibility_timeout: int = None) -> list:
    params = {
        'MaxNumberOfMessages': num_messages,
        'WaitTimeSeconds': WAIT_TIME_SECONDS,
        'MessageAttributeNames': ['All'],
    }
    if visibility_timeout is not None:
        params['VisibilityTimeout'] = visibility_timeout
    return queue.receive_messages(**params)


def get_queue_name(priority: Priority) -> str:
    name = f'TASKHAWK-{settings.TASKHAWK_QUEUE.upper()}'
    if priority is Priority.high:
        name += '-HIGH-PRIORITY'
    elif priority is Priority.low:
        name += '-LOW-PRIORITY'
    elif priority is Priority.bulk:
        name += '-BULK'
    return name


def fetch_and_process_messages(queue_name: str, queue, num_messages: int = 1, visibility_timeout: int = None) -> None:

    for queue_message in get_queue_messages(queue, num_messages, visibility_timeout=visibility_timeout):
        settings.TASKHAWK_PRE_PROCESS_HOOK(queue_name=queue_name, sqs_queue_message=queue_message)

        try:
            message_handler_sqs(queue_message)
            try:
                queue_message.delete()
            except Exception:
                logger.exception(f'Exception while deleting message from {queue_name}')
        except Exception:
            # already logged in message_handler
            pass


def process_messages_for_lambda_consumer(lambda_event: dict) -> None:
    """
    Process messages for a Taskhawk consumer Lambda app, and calls the task function with given `args` and `kwargs`

    If the task function accepts a param called `metadata`, it'll be passed in with a dict containing the metadata
    fields: id, timestamp, version, receipt.

    In case of an exception, the message is kept on Lambda's retry queue and processed again a fixed number of times.
    If the task function keeps failing, Lambda dead letter queue mechanism kicks in and the message is moved to the
    dead-letter queue.
    """
    for record in lambda_event['Records']:
        settings.TASKHAWK_PRE_PROCESS_HOOK(sns_record=record)

        message_handler_lambda(record)


def _close_database():
    if not db:
        return
    for conn in db.connections.all():
        try:
            conn.close()
        except db.InterfaceError:
            pass
        except db.DatabaseError as exc:
            str_exc = str(exc)
            if 'closed' not in str_exc and 'not connected' not in str_exc:
                raise


def listen_for_messages(
        priority: Priority, num_messages: int = 1, visibility_timeout_s: int = None,
        loop_count: int = None) -> None:
    """
    Starts a taskhawk listener for message types provided and calls the task function with given `args` and `kwargs`.

    If the task function accepts a param called `metadata`, it'll be passed in with a dict containing the metadata
    fields: id, timestamp, version, receipt.

    The message is explicitly deleted only if task function ran successfully. In case of an exception the message is
    kept on queue and processed again. If the task function keeps failing, SQS dead letter queue mechanism kicks in and
    the message is moved to the dead-letter queue.

    :param priority: The priority queue to listen to
    :param num_messages: Maximum number of messages to fetch in one SQS API call. Defaults to 1
    :param visibility_timeout_s: The number of seconds the message should remain invisible to other queue readers.
        Defaults to None, which is queue default
    :param loop_count: How many times to fetch messages from SQS. Default to None, which means loop forever.
    """
    queue_name = get_queue_name(priority)

    queue = get_queue(queue_name)
    db_reuse_count = 0
    if loop_count is None:
        while True:
            fetch_and_process_messages(
                queue_name, queue, num_messages=num_messages, visibility_timeout=visibility_timeout_s)
            db_reuse_count += 1
            if db_reuse_count >= settings.TASKHAWK_MAX_DB_REUSE_LOOPS:
                _close_database()
                db_reuse_count = 0
    else:
        for _ in range(loop_count):
            fetch_and_process_messages(
                queue_name, queue, num_messages=num_messages, visibility_timeout=visibility_timeout_s)
