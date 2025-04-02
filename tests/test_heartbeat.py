import threading
from time import sleep
from unittest import mock

from taskhawk.backends.base import TaskhawkConsumerBaseBackend
from taskhawk.heartbeat import start_periodic_heartbeat_hook_thread


class DummyConsumer(TaskhawkConsumerBaseBackend):
    pass


heartbeat_hook = mock.Mock(name='heartbeat_hook')


def test_start_periodic_heartbeat_hook_thread(settings):
    heartbeat_hook.reset_mock()
    consumer = DummyConsumer()
    shutdown_event = threading.Event()
    settings.TASKHAWK_HEARTBEAT_HOOK = 'tests.test_heartbeat.heartbeat_hook'
    settings.TASKHAWK_HEARTBEAT_HOOK_SYNC_CALL_S = 0.4

    heartbeat_hook_thread = start_periodic_heartbeat_hook_thread(consumer, 0.2, shutdown_event)
    sleep(1)
    shutdown_event.set()
    sleep(0.3)

    assert heartbeat_hook.call_count >= 5
    assert not heartbeat_hook_thread.is_alive()
