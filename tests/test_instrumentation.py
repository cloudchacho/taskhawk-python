import json
import random
from unittest import mock

import pytest
from opentelemetry.propagate import set_global_textmap
from opentelemetry.trace import get_tracer, format_trace_id, get_current_span, format_span_id

import taskhawk
from taskhawk import task_manager
from taskhawk.models import Message


@pytest.fixture(autouse=True, scope="module")
def setup_instrumentation():
    import opentelemetry.trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import set_tracer_provider
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    opentelemetry.trace._TRACER_PROVIDER = None

    set_tracer_provider(TracerProvider())
    set_global_textmap(TraceContextTextMapPropagator())

    yield

    opentelemetry.trace._TRACER_PROVIDER = None
    opentelemetry.trace._TRACER_PROVIDER_SET_ONCE._done = False


@pytest.fixture
def trace_id():
    return format_trace_id(random.getrandbits(128))


@pytest.fixture
def message_with_trace(message_data, trace_id):
    span_id = format_span_id(random.getrandbits(64))
    message_data["headers"]["traceparent"] = f"00-{trace_id}-{span_id}-01"
    return Message(message_data)


@pytest.fixture
def queue_message_with_trace(message_with_trace, consumer_backend, backend_provider):
    if backend_provider == "aws":
        from taskhawk.backends import aws
        from tests.helpers.aws import build_aws_sns_record, build_aws_sqs_message

        if isinstance(consumer_backend, aws.AWSSNSConsumerBackend):
            return build_aws_sns_record(message_with_trace)
        elif isinstance(consumer_backend, aws.AWSSQSConsumerBackend):
            message_with_trace.metadata.provider_metadata = aws.AWSMetadata("receipt")
            return build_aws_sqs_message(message_with_trace)
    if backend_provider == "google":
        from taskhawk.backends import gcp
        from tests.helpers.gcp import build_gcp_received_message

        if isinstance(consumer_backend, gcp.GooglePubSubConsumerBackend):
            return build_gcp_received_message(message_with_trace)
    raise ValueError("Unsupported consumer backend type")


@pytest.fixture(name="dummy_task", scope="module")
def _dummy_task():
    @taskhawk.task
    def dummy_task():
        pass

    yield dummy_task
    # unregister the dummy task
    task_manager._ALL_TASKS.pop(dummy_task.task.name, None)


def assert_trace_id_in_context(expected_trace_id):
    def fn(*args, **kwargs):
        context = get_current_span().get_span_context()
        assert format_trace_id(context.trace_id) == expected_trace_id

    return fn


def assert_trace_id_in_publish_message_headers(expected_trace_id):
    def _publish(message, payload, headers):
        assert 'traceparent' in headers
        assert headers['traceparent'].startswith(f'00-{expected_trace_id}-')

    return _publish


@mock.patch('taskhawk.publisher.get_publisher_backend', autospec=True)
def test_task_dispatch_passes_trace_context_in_headers(mock_get_publisher_backend, publisher_backend, dummy_task):
    mock_get_publisher_backend.return_value = publisher_backend
    tracer = get_tracer(__name__)

    with tracer.start_as_current_span(test_task_dispatch_passes_trace_context_in_headers.__name__, {}) as span:
        trace_id = format_trace_id(span.get_span_context().trace_id)
        publisher_backend._publish = mock.MagicMock(side_effect=assert_trace_id_in_publish_message_headers(trace_id))
        dummy_task.dispatch()
        publisher_backend._publish.assert_called_once()


def test_fetch_and_process_message_follows_parent_trace(consumer_backend, queue_message_with_trace, trace_id):
    consumer_backend.pull_messages = mock.MagicMock(return_value=[queue_message_with_trace])
    consumer_backend.process_message = mock.MagicMock(side_effect=assert_trace_id_in_context(trace_id))
    consumer_backend.fetch_and_process_messages()
    consumer_backend.process_message.assert_called_once_with(queue_message_with_trace)


def test_aws_sns_consumer_process_messages_follows_parent_trace(message_with_trace, trace_id):
    aws = pytest.importorskip("taskhawk.backends.aws")

    from tests.helpers.aws import build_aws_sns_record

    record = build_aws_sns_record(message_with_trace)
    consumer = aws.AWSSNSConsumerBackend()
    consumer.process_message = mock.MagicMock(side_effect=assert_trace_id_in_context(trace_id))
    consumer.process_messages({'Records': [record]})

    consumer.process_message.assert_called_once_with(record)


@mock.patch('taskhawk.models.Message.call_task', autospec=True)
def test_message_handler_updates_span_name(mock_call_task, message_with_trace, consumer_backend):
    provider_metadata = mock.Mock()
    tracer = get_tracer(__name__)
    with tracer.start_as_current_span(test_message_handler_updates_span_name.__name__, {}) as span:
        assert span.name == test_message_handler_updates_span_name.__name__
        consumer_backend.message_handler(json.dumps(message_with_trace.as_dict()), provider_metadata)
        assert span.name == message_with_trace.task_name
        assert span.get_span_context().is_valid
        mock_call_task.assert_called_once()
