import logging
import threading
from time import sleep
from typing import Union

from taskhawk.backends.base import TaskhawkConsumerBaseBackend

logger = logging.getLogger(__name__)


def start_periodic_heartbeat_hook_thread(
    consumer_backend: TaskhawkConsumerBaseBackend, delay_s: Union[int, float], shutdown_event: threading.Event
) -> threading.Thread:
    if delay_s <= 0:
        raise ValueError("delay_s must be greater than zero")
    heartbeat_hook_thread = threading.Thread(
        target=periodic_heartbeat_hook, args=(consumer_backend, delay_s, shutdown_event), daemon=True
    )
    heartbeat_hook_thread.start()
    logger.debug("Periodic heartbeat hook thread has started")
    return heartbeat_hook_thread


def periodic_heartbeat_hook(
    consumer_backend: TaskhawkConsumerBaseBackend, delay_s: Union[int, float], shutdown_event: threading.Event
) -> None:
    while not shutdown_event.is_set():
        consumer_backend.call_heartbeat_hook()
        logger.debug("Periodic heartbeat hook was called")
        sleep(delay_s)
