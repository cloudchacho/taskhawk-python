from concurrent.futures import Future
import json
import logging
import typing
import uuid
from decimal import Decimal
from typing import Optional
from unittest import mock

from taskhawk.backends.import_utils import import_class
from taskhawk.conf import settings
from taskhawk.exceptions import (
    ValidationError,
    IgnoreException,
    LoggingException,
    RetryException,
)
from taskhawk.models import Message


logger = logging.getLogger(__name__)


class TaskhawkBaseBackend:
    @classmethod
    def build(cls, dotted_path: str, *args, **kwargs):
        """
        Import a dotted module path and return the backend class instance.
        Raise ImportError if the import failed.
        """
        backend_cls = import_class(dotted_path)
        return backend_cls(*args, **kwargs)

    @staticmethod
    def message_payload(data: dict) -> str:
        return json.dumps(data, default=_decimal_json_default, allow_nan=False)


class TaskhawkPublisherBaseBackend(TaskhawkBaseBackend):
    def _dispatch_sync(self, message: Message) -> None:
        from taskhawk.backends.utils import get_consumer_backend

        consumer_backend = get_consumer_backend(priority=message.priority)
        queue_message = self._mock_queue_message(message)
        settings.TASKHAWK_PRE_PROCESS_HOOK(**consumer_backend.pre_process_hook_kwargs(queue_message))
        consumer_backend.process_message(queue_message)
        settings.TASKHAWK_POST_PROCESS_HOOK(**consumer_backend.post_process_hook_kwargs(queue_message))

    def _mock_queue_message(self, message: Message) -> mock.Mock:
        raise NotImplementedError

    def _publish(
        self,
        message: Message,
        payload: str,
        headers: typing.Optional[typing.Mapping] = None,
    ) -> typing.Union[str, Future]:
        raise NotImplementedError

    def publish(self, message: Message) -> typing.Union[str, Future]:
        if settings.TASKHAWK_SYNC:
            self._dispatch_sync(message)
            return str(uuid.uuid4())

        message_body = message.as_dict()
        headers = {**message_body["headers"]}
        payload = self.message_payload(message_body)

        result = self._publish(message, payload, headers)

        log_published_message(message_body, result)

        return result


class TaskhawkConsumerBaseBackend(TaskhawkBaseBackend):
    @staticmethod
    def pre_process_hook_kwargs(queue_message) -> dict:
        return {}

    @staticmethod
    def post_process_hook_kwargs(queue_message) -> dict:
        return {}

    def message_handler(self, message_json: str, provider_metadata) -> None:
        message = self._build_message(message_json, provider_metadata)
        _log_received_message(message.as_dict())

        message.call_task()

    def fetch_and_process_messages(self, num_messages: int = 1, visibility_timeout: Optional[int] = None) -> None:
        queue_messages = self.pull_messages(num_messages, visibility_timeout)
        for queue_message in queue_messages:
            try:
                settings.TASKHAWK_PRE_PROCESS_HOOK(**self.pre_process_hook_kwargs(queue_message))
            except Exception:
                logger.exception('Exception in post process hook for message', extra={'queue_message': queue_message})
                continue

            try:
                self.process_message(queue_message)
            except IgnoreException:
                logger.info('Ignoring task', extra={'queue_message': queue_message})
            except LoggingException as e:
                # log with message and extra
                logger.exception(str(e), extra=e.extra)
                continue
            except RetryException:
                # Retry without logging exception
                logger.info('Retrying due to exception')
                continue
            except Exception:
                logger.exception('Exception while processing message')
                continue

            try:
                settings.TASKHAWK_POST_PROCESS_HOOK(**self.post_process_hook_kwargs(queue_message))
            except Exception:
                logger.exception('Exception in post process hook for message', extra={'queue_message': queue_message})
                continue

            try:
                self.delete_message(queue_message)
            except Exception:
                logger.exception('Exception while deleting message', extra={'queue_message': queue_message})

    def extend_visibility_timeout(self, visibility_timeout_s: int, metadata) -> None:
        """
        Extends visibility timeout of a message on a given priority queue for long running tasks.
        """
        raise NotImplementedError

    def requeue_dead_letter(self, num_messages: int = 10, visibility_timeout: Optional[int] = None) -> None:
        """
        Re-queues everything in the Taskhawk DLQ back into the Taskhawk queue.
        """
        raise NotImplementedError

    def pull_messages(self, num_messages: int = 1, visibility_timeout: Optional[int] = None) -> typing.List:
        """
        Pulls messages from the cloud for this app.
        :param num_messages:
        :param visibility_timeout:
        :return: a tuple of list of messages and the queue they were pulled from
        """
        raise NotImplementedError

    def process_message(self, queue_message) -> None:
        raise NotImplementedError

    def process_messages(self, lambda_event) -> None:
        # for lambda backend
        raise NotImplementedError

    def delete_message(self, queue_message) -> None:
        raise NotImplementedError

    @staticmethod
    def _build_message(message_json: str, provider_metadata) -> Message:
        try:
            message = Message(json.loads(message_json))
            message.metadata.provider_metadata = provider_metadata
            return message
        except (ValidationError, ValueError):
            _log_invalid_message(message_json)
            raise

    @property
    def error_count(self) -> int:
        raise NotImplementedError


def _decimal_json_default(obj):
    if isinstance(obj, Decimal):
        int_val = int(obj)
        if int_val == obj:
            return int_val
        else:
            return float(obj)
    raise TypeError


def log_published_message(message_body: dict, result: typing.Union[str, Future]) -> None:
    def _log(message_id: str):
        logger.debug('Sent message', extra={'message_body': message_body, 'message_id': message_id})

    if isinstance(result, Future):
        result.add_done_callback(lambda f: _log(f.result()))
    else:
        _log(result)


def _log_received_message(message_body: dict) -> None:
    logger.debug('Received message', extra={'message_body': message_body})


def _log_invalid_message(message_json: str) -> None:
    logger.error('Received invalid message', extra={'message_json': message_json})
