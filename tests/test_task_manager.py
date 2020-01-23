from unittest import mock
import uuid

import pytest

from taskhawk.task_manager import _ALL_TASKS, Task, task, AsyncInvocation
from taskhawk.models import Priority
from taskhawk.exceptions import ConfigurationError, TaskNotFound
from .tasks import send_email


def test_task_decorator():
    @task
    def f():
        pass

    assert f.task.name == 'tests.test_task_manager.f'
    assert callable(f.dispatch)
    assert callable(f.with_headers)
    assert callable(f.with_priority)
    assert 'tests.test_task_manager.f' in _ALL_TASKS


def test_task_decorator_custom_name():
    @task(name='foo')
    def f():
        pass

    assert f.task.name == 'foo'
    assert 'foo' in _ALL_TASKS


def test_task_decorator_custom_name_conflict():
    def make_tasks():
        @task(name='foo')
        def f():
            pass

        @task(name='foo')
        def g():
            pass

    with pytest.raises(ConfigurationError):
        make_tasks()


def test_task_decorator_priority():
    @task(priority=Priority.high, name='test_task_decorator_priority')
    def f():
        pass

    assert f.task.priority == Priority.high
    assert callable(f.dispatch)
    assert callable(f.with_headers)
    assert callable(f.with_priority)
    assert 'test_task_decorator_priority' in _ALL_TASKS


default_headers_hook = mock.MagicMock()


@pytest.fixture(name='invocation')
def _invocation():
    return AsyncInvocation(send_email.task)


def test_async_invocation_with_headers(invocation):
    request_id = str(uuid.uuid4())
    assert invocation is invocation.with_headers(request_id=request_id)
    assert invocation._headers == {'request_id': request_id}


def test_async_invocation_with_priority(invocation):
    assert invocation is invocation.with_priority(Priority.high)
    assert invocation._priority == Priority.high


@mock.patch('taskhawk.task_manager.publish', autospec=True)
@mock.patch('taskhawk.models.Message.new')
def test_async_invocation_dispatch(mock_message_new, mock_publish, invocation, message):
    args = ('example@email.com', 'Hello!')
    kwargs = {'from_email': 'example@spammer.com'}

    mock_message_new.return_value.as_dict.return_value = message.as_dict()

    invocation.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

    mock_message_new.assert_called_once_with(invocation._task.name, Priority.default, args, kwargs, headers={})
    mock_publish.assert_called_once_with(mock_message_new.return_value)


@mock.patch('taskhawk.task_manager.publish', autospec=True)
@mock.patch('taskhawk.models.Message.new')
def test_async_invocation_dispatch_custom_priority(mock_message_new, mock_publish, invocation, message):
    invocation = invocation.with_priority(Priority.high)

    args = ('example@email.com', 'Hello!')
    kwargs = {'from_email': 'example@spammer.com'}

    mock_message_new.return_value.as_dict.return_value = message.as_dict()

    invocation.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

    mock_message_new.assert_called_once_with(invocation._task.name, invocation._priority, args, kwargs, headers={})
    mock_publish.assert_called_once_with(mock_message_new.return_value)


@mock.patch('uuid.uuid4')
@mock.patch('taskhawk.task_manager.publish', autospec=True)
@mock.patch('taskhawk.models.Message.new')
def test_async_invocation_dispatch_default_headers(mock_message_new, mock_publish, mock_uuid, message, settings):
    mock_uuid.return_value = str(uuid.uuid4())

    settings.TASKHAWK_DEFAULT_HEADERS = 'tests.test_task_manager.default_headers_hook'
    default_headers_hook.return_value = {'mickey': 'mouse'}

    invocation = AsyncInvocation(send_email.task)

    args = ('example@email.com', 'Hello!')
    kwargs = {'from_email': 'example@spammer.com'}

    mock_message_new.return_value.as_dict.return_value = message.as_dict()

    invocation.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

    default_headers_hook.assert_called_once_with(task=send_email.task)
    mock_message_new.assert_called_once_with(
        invocation._task.name, Priority.default, args, kwargs, headers=default_headers_hook.return_value
    )
    mock_publish.assert_called_once_with(mock_message_new.return_value)


class TestTask:
    @staticmethod
    def f(a, b, c=1):
        pass

    @staticmethod
    def f_metadata_headers(a, b, metadata, headers=None, c=1):
        pass

    @staticmethod
    def f_kwargs(a, b, **kwargs):
        pass

    @staticmethod
    def f_args(a, b, *args, **kwargs):
        pass

    @staticmethod
    def f_invalid_annotation(a, b, metadata: int):
        pass

    @staticmethod
    def f_invalid_annotation2(a, b, headers: int):
        pass

    def test_constructor(self):
        task_obj = Task(TestTask.f, Priority.default, 'name')
        assert task_obj.name == 'name'
        assert task_obj.fn is TestTask.f
        assert task_obj.priority is Priority.default
        assert task_obj._accepts_metadata is False
        assert task_obj._accepts_headers is False

    def test_constructor_accepts_metadata_and_headers(self):
        task_obj = Task(TestTask.f_metadata_headers, Priority.default, 'name')
        assert task_obj.name == 'name'
        assert task_obj.fn is TestTask.f_metadata_headers
        assert task_obj.priority is Priority.default
        assert task_obj._accepts_metadata is True
        assert task_obj._accepts_headers is True

    def test_constructor_kwargs(self):
        task_obj = Task(TestTask.f_kwargs, Priority.default, 'name')
        assert task_obj.name == 'name'
        assert task_obj.fn is TestTask.f_kwargs
        assert task_obj.priority is Priority.default
        assert task_obj._accepts_metadata is True
        assert task_obj._accepts_headers is True

    def test_constructor_disallow_args(self):
        with pytest.raises(ConfigurationError):
            Task(TestTask.f_args, Priority.default, 'name')

    def test_constructor_bad_annotation(self):
        with pytest.raises(ConfigurationError):
            Task(TestTask.f_invalid_annotation, Priority.default, 'name')

    def test_constructor_bad_annotation2(self):
        with pytest.raises(ConfigurationError):
            Task(TestTask.f_invalid_annotation2, Priority.default, 'name')

    def test_with_headers(self):
        task_obj = Task(TestTask.f, Priority.default, 'name')
        request_id = str(uuid.uuid4())
        assert task_obj.with_headers(request_id=request_id)._headers == {'request_id': request_id}

    def test_with_priority(self):
        task_obj = Task(TestTask.f, Priority.default, 'name')
        assert task_obj.with_priority(Priority.high)._priority == Priority.high

    @mock.patch('taskhawk.task_manager.AsyncInvocation.dispatch', autospec=True)
    def test_dispatch(self, mock_dispatch):
        task_obj = Task(TestTask.f, Priority.default, 'name')
        task_obj.dispatch(1, 2)
        mock_dispatch.assert_called_once()
        assert mock_dispatch.call_args[0][1:] == (1, 2)

    def test_call(self, message):
        _f = mock.MagicMock()

        @task(name='test_call')
        def f(to: str, subject: str, from_email: str = None):
            _f(to, subject, from_email=from_email)

        task_obj = f.task
        task_obj.call(message)
        _f.assert_called_once_with(*message.args, **message.kwargs)

    def test_call_headers(self, message):
        _f = mock.MagicMock()

        @task(name='test_call_headers')
        def f(to: str, subject: str, from_email: str = None, headers=None):
            _f(to, subject, from_email=from_email, headers=headers)

        task_obj = f.task
        task_obj.call(message)
        _f.assert_called_once_with(*message.args, headers=message.headers, **message.kwargs)

    def test_call_metadata(self, message):
        _f = mock.MagicMock()

        @task(name='test_call_metadata')
        def f(to: str, subject: str, metadata, from_email: str = None):
            _f(to, subject, metadata, from_email=from_email)

        task_obj = f.task
        task_obj.call(message)
        _f.assert_called_once_with(*message.args, message.metadata, **message.kwargs)

    def test_find_by_name(self):
        assert Task.find_by_name('tests.tasks.send_email') == send_email.task

    def test_find_by_name_fail(self):
        with pytest.raises(TaskNotFound):
            Task.find_by_name('invalid')

    def test_repr(self):
        assert str(send_email.task) == 'Taskhawk task: tests.tasks.send_email'
