from functools import lru_cache

from taskhawk.conf import settings


@lru_cache(maxsize=5)
def get_publisher_backend(*args, **kwargs):
    from taskhawk.backends.base import TaskhawkPublisherBaseBackend

    return TaskhawkPublisherBaseBackend.build(settings.TASKHAWK_PUBLISHER_BACKEND, *args, **kwargs)


@lru_cache(maxsize=5)
def get_consumer_backend(*args, **kwargs):
    from taskhawk.backends.base import TaskhawkConsumerBaseBackend

    return TaskhawkConsumerBaseBackend.build(settings.TASKHAWK_CONSUMER_BACKEND, *args, **kwargs)
