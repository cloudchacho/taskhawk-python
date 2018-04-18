import logging
import time
import uuid

import pytest

from taskhawk import Message
import taskhawk.conf
# initialize tasks
import tests.tasks  # noqa


def pytest_configure():
    logging.basicConfig()


@pytest.fixture
def settings():
    """
    Use this fixture to override settings. Changes are automatically reverted
    """
    overrides = {}
    original_module = taskhawk.conf.settings._user_settings

    class Wrapped:
        def __getattr__(self, name):
            return overrides.get(name, getattr(original_module, name))

    taskhawk.conf.settings._user_settings = Wrapped()
    taskhawk.conf.settings.clear_cache()

    try:
        yield taskhawk.conf.settings._user_settings
    finally:
        taskhawk.conf.settings._user_settings = original_module
        taskhawk.conf.settings.clear_cache()


@pytest.fixture(name='message_data')
def _message_data():
    return {
        "id": "b1328174-a21c-43d3-b303-964dfcc76efc",
        "metadata": {
            "timestamp": int(time.time() * 1000),
            "version": "1.0",
            "priority": "default"
        },
        "headers": {
            'request_id': str(uuid.uuid4()),
        },
        "task": "tests.tasks.send_email",
        "args": [
            "example@email.com",
            "Hello!",
        ],
        "kwargs": {
            "from_email": "hello@spammer.com"
        },
    }


@pytest.fixture()
def message(message_data):
    return Message(message_data)
