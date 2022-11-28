import enum
import time
import typing
import uuid
from typing import Optional

import arrow
import arrow.parser

from taskhawk.backends.utils import get_consumer_backend
from taskhawk.exceptions import TaskNotFound, ValidationError

if typing.TYPE_CHECKING:
    from taskhawk.task_manager import Task  # noqa  # pragma: no cover


class Metadata:
    def __init__(self, data: dict) -> None:
        self._id: str = data['id']
        self._priority: Priority = Priority[data['metadata']['priority']]
        self._version: str = data['metadata']['version']
        self._timestamp: int = data['metadata']['timestamp']
        self._headers: dict = data['headers']
        self._provider_metadata = None

    @property
    def id(self) -> str:
        """
        Task id
        """
        return self._id

    @property
    def version(self):
        """
        Task message format version
        """
        return self._version

    @property
    def priority(self) -> 'Priority':
        return self._priority

    @priority.setter
    def priority(self, value: 'Priority') -> None:
        self._priority = value

    @property
    def timestamp(self) -> int:
        """
        Timestamp of message creation in epoch milliseconds
        """
        return self._timestamp

    @timestamp.setter
    def timestamp(self, value: int) -> None:
        self._timestamp = value

    @property
    def provider_metadata(self):
        """
        Provider specific metadata, such as SQS Receipt, or Google ack id. This may be used to extend message
        visibility if the task is running longer than expected using :meth:`Message.extend_visibility_timeout`
        """
        return self._provider_metadata

    @provider_metadata.setter
    def provider_metadata(self, value) -> None:
        """
        Set the provider metadata
        """
        self._provider_metadata = value

    @property
    def headers(self) -> dict:
        """
        Custom headers sent with the message
        """
        return self._headers.copy()

    def as_dict(self) -> dict:
        # not all fields since some fields are serialized at top-level (see Message.__init__ for details)
        return {"timestamp": self.timestamp, "priority": self.priority.name, "version": self.version}

    def full_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "priority": self.priority.name,
            "version": self.version,
            "headers": self.headers,
        }

    def extend_visibility_timeout(self, visibility_timeout_s: int) -> None:
        """
        Extends visibility timeout of a message for long running tasks.
        """
        consumer_backend = get_consumer_backend(priority=self.priority)
        consumer_backend.extend_visibility_timeout(visibility_timeout_s, self.provider_metadata)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.full_dict() == typing.cast(Metadata, other).full_dict()


class Message:
    """
    Model for Taskhawk messages. All properties of a message should be considered immutable.
    """

    CURRENT_VERSION = '1.0'
    VERSIONS = ['1.0']

    def __init__(self, data: dict) -> None:
        """
        data will look like this:
        {
            "id": "b1328174-a21c-43d3-b303-964dfcc76efc",
            "metadata": {
                "priority": "high",
                "timestamp": 1460868253255,
                "version": "1.0"
            },
            "headers": {
                ...
            },
            "task": "tasks.send_email",
            "args": [
                "email@automatic.com",
                "Hello!"
            ],
            "kwargs": {
                "from_email": "spam@example.com"
            }
        }
        """
        self.validate_data(data)

        self._metadata: Metadata = Metadata(data)
        self._task_name: str = data['task']
        self._args: list = data['args']
        self._kwargs: dict = data['kwargs']

        self.validate()

    def validate_data(self, data: dict) -> None:
        """
        Validate that message data contains all the right things.
        :raises exceptions.ValidationError: when message fails validation
        """
        if (
            not data.get('id')
            or not data.get('metadata')
            or not isinstance(data['metadata'], dict)
            or not data['metadata'].get('version')
            or data['metadata']['version'] not in self.VERSIONS
            or not data['metadata'].get('timestamp')
            or data.get('headers') is None
            or not data.get('task')
            or data.get('args') is None
            or data.get('kwargs') is None
        ):
            raise ValidationError

        # support string datetimes
        if isinstance(data['metadata']['timestamp'], str):
            try:
                data['metadata']['timestamp'] = int(arrow.get(data['metadata']['timestamp']).float_timestamp * 1000)
            except (ValueError, arrow.parser.ParserError):
                raise ValidationError

    def validate(self) -> None:
        """
        Validate that message object contains all the right things.
        :raises exceptions.ValidationError: when message fails validation
        """
        from taskhawk.task_manager import Task  # noqa

        try:
            self._task: Task = Task.find_by_name(self.task_name)
        except TaskNotFound:
            raise ValidationError

    @classmethod
    def _create_metadata(cls, priority: 'Priority') -> dict:
        return {'priority': priority.name, 'timestamp': int(time.time() * 1000), 'version': cls.CURRENT_VERSION}

    @classmethod
    def new(
        cls,
        task: str,
        priority: 'Priority',
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        msg_id: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> 'Message':
        """
        Creates Message object given type, schema version and data. This is typically used by the publisher code.
        :param task: The task name
        :param priority: The task priority
        :param args: The list of args
        :param kwargs: The dict of kwargs
        :param msg_id: Optional message identifier.  If unset, a random UUID4 will be generated.
        :param headers: Optional additional headers
        """
        return Message(
            {
                'id': msg_id or str(uuid.uuid4()),
                'metadata': cls._create_metadata(priority),
                'headers': headers or {},
                'task': task,
                'args': args or [],
                'kwargs': kwargs or {},
            }
        )

    def call_task(self) -> None:
        """
        Call the task with this message
        """
        self.task.call(self)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.as_dict() == typing.cast(Message, other).as_dict()

    @property
    def metadata(self) -> Metadata:
        return self._metadata

    @property
    def id(self) -> str:
        return self.metadata.id

    id.__doc__ = Metadata.id.__doc__

    @property
    def priority(self) -> 'Priority':
        return self.metadata.priority

    priority.__doc__ = Metadata.priority.__doc__

    @property
    def timestamp(self) -> int:
        return self.metadata.timestamp

    timestamp.__doc__ = Metadata.timestamp.__doc__

    @property
    def headers(self) -> dict:
        return self._metadata.headers

    headers.__doc__ = Metadata.headers.__doc__

    @property
    def version(self) -> str:
        return self._metadata.version

    version.__doc__ = Metadata.version.__doc__

    @property
    def provider_metadata(self):
        return self.metadata.provider_metadata

    provider_metadata.__doc__ = Metadata.provider_metadata.__doc__

    @property
    def task(self) -> 'Task':
        assert self._task
        return self._task

    @property
    def task_name(self) -> str:
        return self._task_name

    @property
    def args(self) -> list:
        return self._args

    @property
    def kwargs(self) -> dict:
        return self._kwargs

    def items(self) -> typing.ItemsView:
        return self.as_dict().items()

    def as_dict(self) -> dict:
        return {
            'id': self.id,
            'metadata': self.metadata.as_dict(),
            'headers': self.headers,
            'task': self.task_name,
            'args': self.args,
            'kwargs': self.kwargs,
        }


class Priority(enum.Enum):
    """
    Priority of a task. This may be used to differentiate batch jobs from other tasks for example.

    High and low priority queues provide independent scaling knobs for your use-case.
    """

    default = enum.auto()
    """
    This is the default priority of a task if nothing is specified. In most cases,
    using just the default queue should work fine.
    """

    high = enum.auto()
    low = enum.auto()

    bulk = enum.auto()
    """
    Bulk queue will typically have different monitoring, and may be used for bulk jobs,
    such as sending push notifications to all users. This allows you to effectively
    throttle the tasks.
    """
