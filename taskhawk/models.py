import enum
import typing
import uuid

import time

from taskhawk.exceptions import TaskNotFound, ValidationError


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
                "timestamp": 1460868253255,
                "version": "1.0"
            },
            "headers": {
                ...
            },
            "task": "tasks.send_email",
            "args": [
                "aniruddha@automatic.com",
                "Hello!"
            ],
            "kwargs": {
                "from_email": "hello@automatic.com"
            }
        }
        """
        self._id = data['id']
        self._metadata = data['metadata'] or {}
        self._headers = data['headers']
        self._task_name = data['task']
        self._args = data['args']
        self._kwargs = data['kwargs']

        # will be assigned during validation:
        self._task = None

    def validate(self) -> None:
        """
        Validate that message object contains all the right things.
        :raises exceptions.ValidationError: when message fails validation
        """
        from taskhawk.task_manager import Task

        if (not self.id or not self.version or self.version not in self.VERSIONS or not self.timestamp or
                self.headers is None or not self.task_name or self.args is None or self.kwargs is None):
            raise ValidationError
        try:
            self._task = Task.find_by_name(self.task_name)
        except TaskNotFound:
            raise ValidationError

    @classmethod
    def _create_metadata(cls) -> dict:
        return {
            'timestamp': int(time.time() * 1000),
            'version': cls.CURRENT_VERSION
        }

    @classmethod
    def new(cls, task: str, args: tuple=None, kwargs: dict=None, msg_id: str=None, headers: dict=None) -> 'Message':
        """
        Creates Message object given type, schema version and data. This is typically used by the publisher code.
        :param task: The task name
        :param args: The list of args
        :param kwargs: The dict of kwargs
        :param msg_id: Optional message identifier.  If unset, a random UUID4 will be generated.
        :param headers: Optional additional headers
        """
        return Message({
            'id': msg_id or str(uuid.uuid4()),
            'metadata': cls._create_metadata(),
            'headers': headers or {},
            'task': task,
            'args': args or [],
            'kwargs': kwargs or {},
        })

    def call_task(self, receipt: typing.Optional[str]) -> None:
        """
        Call the task with this message
        """
        self.task.call(self, receipt)

    def __eq__(self, other) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.as_dict() == other.as_dict()

    @property
    def id(self) -> str:
        return self._id

    @property
    def metadata(self) -> str:
        return self._metadata

    @property
    def timestamp(self) -> int:
        return self._metadata.get('timestamp')

    @property
    def version(self) -> int:
        return self._metadata.get('version')

    @property
    def headers(self) -> dict:
        return self._headers

    @property
    def task(self) -> 'taskhawk.Task':
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
            'metadata': self.metadata,
            'headers': self.headers,
            'task': self.task_name,
            'args': self.args,
            'kwargs': self.kwargs,
        }


class Priority(enum.Enum):
    """
    Priority of a task. This may be used to differentiate batch jobs from other tasks for example.
    """
    default = enum.auto()
    high = enum.auto()
    low = enum.auto()
    bulk = enum.auto()
