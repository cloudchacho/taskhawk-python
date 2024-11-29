import json
from time import time
from unittest import mock

import arrow
from google.pubsub_v1 import ReceivedMessage, PubsubMessage

from taskhawk.models import Message


def build_gcp_received_message(message: Message) -> ReceivedMessage:
    queue_message = mock.create_autospec(ReceivedMessage)
    queue_message.ack_id = "dummy_ack_id"
    queue_message.message = mock.create_autospec(PubsubMessage)
    queue_message.message.message_id = str(time())
    queue_message.message.data = json.dumps(message.as_dict()).encode()
    queue_message.message.attributes = message.as_dict()['headers']
    queue_message.message.publish_time = arrow.utcnow().datetime
    queue_message.delivery_attempt = 1
    return queue_message
