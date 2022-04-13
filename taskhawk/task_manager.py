import copy
import inspect
import typing
from concurrent.futures import Future

from taskhawk.conf import settings
from taskhawk.exceptions import ConfigurationError, TaskNotFound
from taskhawk.models import Metadata, Message, Priority
from taskhawk.publisher import publish


_ALL_TASKS: dict = {}


def task(*args, priority: Priority = Priority.default, name: typing.Optional[str] = None) -> typing.Any:
    """
    Decorator for taskhawk task functions. Any function may be converted into a task by adding this decorator
    as such:

    .. code:: python

        @taskhawk.task
        def send_email(to: str, subject: str, from: str = None) -> None:
            ...

    Additional methods available on tasks are described by :class:`taskhawk.Task` class
    """

    def _decorator(fn: typing.Any) -> typing.Callable:
        task_name = name or f'{fn.__module__}.{fn.__name__}'
        existing_task = _ALL_TASKS.get(task_name)
        if existing_task is not None:
            func = existing_task.fn
            raise ConfigurationError(f'Task named "{task_name}" already exists: {func.__module__}.{func.__name__}')

        fn.task = Task(fn, priority, task_name)
        fn.dispatch = fn.task.dispatch
        fn.with_headers = fn.task.with_headers
        fn.with_priority = fn.task.with_priority
        _ALL_TASKS[fn.task.name] = fn.task
        return fn

    if len(args) == 1 and callable(args[0]):
        # No arguments, this is the decorator
        return _decorator(args[0])

    return _decorator


class AsyncInvocation:
    """
    Represents one particular invocation of a task. An invocation may be customized using `with_` functions,
    and these won't affect other invocations of the same task. Invocations may also be saved and re-used multiple times.
    """

    def __init__(self, task_: 'Task') -> None:
        self._task = task_
        self._headers: dict = {}
        self._priority: typing.Optional[Priority] = None

    def with_headers(self, **headers) -> 'AsyncInvocation':
        """
        Customize headers for this invocation
        :param headers: Arbitrary headers dict
        :return: updated invocation that uses custom headers
        """
        self._headers.update(headers)
        return self

    def with_priority(self, priority: Priority) -> 'AsyncInvocation':
        """
        Customize priority for this invocation
        :param priority: Custom priority to attach to this invocation
        :return: updated invocation that uses custom priority
        """
        assert isinstance(priority, Priority)
        # don't clobber existing value
        assert self._priority is None
        self._priority = priority
        return self

    def dispatch(self, *args, **kwargs) -> typing.Union[str, Future]:
        """
        Dispatch task for async execution
        :param args: arguments to pass to the task
        :param kwargs: keyword args to pass to the task
        :returns: for async publishers, returns a future that represents the publish api call, otherwise, returns
        the published message id
        """
        message = Message.new(
            self._task.name,
            self._priority or self._task.priority,
            copy.deepcopy(args),
            copy.deepcopy(kwargs),
            headers={**settings.TASKHAWK_DEFAULT_HEADERS(task=self._task), **self._headers},
        )
        return publish(message)


class Task:
    """
    Represents a Taskhawk task. This class provides methods to dispatch tasks asynchronously,
    You can also chain customizations such as:

    .. code:: python

        send_email.with_headers(request_id='1234')\\
                  .with_priority(taskhawk.Priority.high)\\
                  .dispatch('example@email.com')

    These customizations may also be saved and re-used multiple times

    .. code:: python

        send_email_high_priority = send_email.with_priority(taskhawk.Priority.high)

        send_email_high_priority.dispatch('example@email.com')

        send_email_high_priority.with_headers(request_id='1234')\\
                                .dispatch('example@email.com')

    """

    def __init__(self, fn: typing.Callable, priority: Priority, name: str) -> None:
        self._name = name
        self._fn = fn
        self._priority = priority
        signature = inspect.signature(fn)
        self._accepts_metadata = False
        self._accepts_headers = False
        for p in signature.parameters.values():
            # if **kwargs is specified, just pass all things by default since function can always inspect arg names
            if p.kind == inspect.Parameter.VAR_KEYWORD:
                self._accepts_metadata = self._accepts_headers = True
            elif p.kind == inspect.Parameter.VAR_POSITIONAL:
                # disallow use of *args
                raise ConfigurationError("Use of *args is not allowed")
            elif p.name == "metadata":
                if p.annotation is not inspect.Signature.empty and p.annotation is not Metadata:
                    raise ConfigurationError(f"Signature for 'metadata' param must be Metadata, not {p.annotation}")
                self._accepts_metadata = True
            elif p.name == "headers":
                if p.annotation is not inspect.Signature.empty and p.annotation is not dict:
                    raise ConfigurationError("Signature for 'headers' param must be dict")
                self._accepts_headers = True

    @property
    def name(self) -> str:
        """
        :return: Task name
        """
        return self._name

    @property
    def priority(self) -> Priority:
        """
        :return: Priority
        """
        return self._priority

    @property
    def fn(self) -> typing.Callable:
        """ "
        return: Task function
        """
        return self._fn

    @property
    def accepts_metadata(self) -> bool:
        """
        :return: Flag indicating if task accepts metadata
        """
        return self._accepts_metadata

    @property
    def accepts_headers(self) -> bool:
        """
        :return: Flag indicating if task accepts headers
        """
        return self._accepts_headers

    def with_headers(self, **headers) -> AsyncInvocation:
        """
        Create a task invocation that uses custom headers

        :param headers: Arbitrary headers
        :return: an invocation that uses custom headers
        """
        return AsyncInvocation(self).with_headers(**headers)

    def with_priority(self, priority: Priority) -> AsyncInvocation:
        """
        Create a task invocation with custom priority

        :param priority: Custom priority to attach to this invocation
        :return: an invocation that uses custom priority
        """
        return AsyncInvocation(self).with_priority(priority)

    def dispatch(self, *args, **kwargs) -> None:
        """
        Dispatch task for async execution

        :param args: arguments to pass to the task
        :param kwargs: keyword args to pass to the task
        """
        AsyncInvocation(self).dispatch(*args, **kwargs)

    def call(self, message: "Message") -> None:
        """
        Calls the task with this message
        :param message: The message
        """
        args = copy.deepcopy(message.args)
        kwargs = copy.deepcopy(message.kwargs)
        if self.accepts_metadata:
            kwargs["metadata"] = message.metadata
        if self.accepts_headers:
            kwargs["headers"] = copy.deepcopy(message.headers)
        self.fn(*args, **kwargs)

    def __str__(self) -> str:
        return f"Taskhawk task: {self.name}"

    @classmethod
    def find_by_name(cls, name: str) -> "Task":
        """
        Finds a task by name
        :param name: task name (including module)
        :return: Task
        :raises TaskNotFound: if task isn't registered
        """
        if name in _ALL_TASKS:
            return _ALL_TASKS[name]
        raise TaskNotFound(name)
