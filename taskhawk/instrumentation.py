from contextlib import contextmanager
from typing import Dict, Optional, Iterator

from opentelemetry import trace
from opentelemetry.propagate import inject, extract
from opentelemetry.trace import Span

from taskhawk.models import Message


@contextmanager
def on_receive(sns_record=None, sqs_queue_message=None, google_pubsub_message=None) -> Iterator[Span]:
    """
    Hook for instrumenting consumer after message is dequeued. If applicable, starts a new span.
    :param sns_record:
    :param sqs_queue_message:
    :param google_pubsub_message:
    :return:
    """
    attributes: Optional[Dict]
    if sqs_queue_message is not None:
        attributes = _get_attributes_from_aws_sqs_queue_message(sqs_queue_message)
    elif sns_record is not None:
        attributes = _get_attributes_from_aws_sns_record(sns_record)
    elif google_pubsub_message is not None:
        attributes = google_pubsub_message.message.attributes
    else:
        attributes = None
    tracectx = extract(attributes)

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("message_received", context=tracectx, kind=trace.SpanKind.CONSUMER) as span:
        yield span


def _get_attributes_from_aws_sqs_queue_message(sqs_queue_message) -> Dict[str, str]:
    return {
        key: message_attribute["StringValue"]
        for key, message_attribute in sqs_queue_message.message_attributes.items()
        if message_attribute["DataType"] == "String"
    }


def _get_attributes_from_aws_sns_record(sns_record) -> Dict[str, str]:
    return {
        key: message_attribute["Value"]
        for key, message_attribute in sns_record["Sns"]["MessageAttributes"].items()
        if message_attribute["Type"] == "String"
    }


def on_message(message: Message) -> None:
    """
    Hook for instrumenting consumer after message is deserialized and validated. If applicable, updates the current span
    with the right name.
    :param message:
    :return:
    """
    span = trace.get_current_span()
    span.update_name(message.task_name)


@contextmanager
def on_publish(message: Message, headers: Dict) -> Iterator[Span]:
    """
    Hook for instrumenting publish. If applicable, injects tracing headers into headers dictionary.
    :param message:
    :param headers:
    :return:
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(f"publish/{message.task_name}", kind=trace.SpanKind.PRODUCER) as span:
        inject(headers)
        yield span
