"""
taskhawk
~~~~~~~~

:copyright: (c) 2013-2017 by the Automatic Labs.
"""


# semantic versioning (http://semver.org/)
VERSION = '4.2.0'


try:
    from .backends.aws import AWSMetadata  # noqa
except ImportError:
    pass
try:
    from .backends.gcp import GoogleMetadata  # noqa
except ImportError:
    pass
from .commands import requeue_dead_letter  # noqa
from .consumer import listen_for_messages, process_messages_for_lambda_consumer  # noqa
from .exceptions import *  # noqa
from .models import Metadata, Priority  # noqa
from .publisher import publish  # noqa
from .task_manager import AsyncInvocation, task, Task  # noqa
