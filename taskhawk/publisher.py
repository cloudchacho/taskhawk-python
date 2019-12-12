import typing
from concurrent.futures import Future

from taskhawk.backends.base import TaskhawkPublisherBaseBackend
from taskhawk.backends.utils import get_publisher_backend
from taskhawk.models import Message


def publish(message: Message, backend: TaskhawkPublisherBaseBackend = None) -> typing.Union[str, Future]:
    """
    Publishes a message on Taskhawk topic
    """
    backend = backend or get_publisher_backend(priority=message.priority)
    return backend.publish(message)
