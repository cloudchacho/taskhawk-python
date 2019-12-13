import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Generator, Any

from taskhawk.conf import settings


@lru_cache(maxsize=5)
def get_publisher_backend(*args, **kwargs):
    from taskhawk.backends.base import TaskhawkPublisherBaseBackend

    return TaskhawkPublisherBaseBackend.build(settings.TASKHAWK_PUBLISHER_BACKEND, *args, **kwargs)


@lru_cache(maxsize=5)
def get_consumer_backend(*args, **kwargs):
    from taskhawk.backends.base import TaskhawkConsumerBaseBackend

    return TaskhawkConsumerBaseBackend.build(settings.TASKHAWK_CONSUMER_BACKEND, *args, **kwargs)


@contextmanager
def override_env(env: str, value: Any) -> Generator[None, None, None]:
    """
    Override environment variable value temporarily
    """
    orig_value = os.environ.get(env)

    os.environ[env] = value

    try:
        yield
    finally:
        # was the value originally set? if so, restore it
        if orig_value is not None:
            os.environ[env] = orig_value
        else:
            # value wasn't set originally, so unset it again
            del os.environ[env]
