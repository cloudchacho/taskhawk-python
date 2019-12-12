Configuration
=============

Add appropriate configuration to the app. If not using a Django app, ensure that `SETTINGS_MODULE` is
defined to the path of a module where all settings can be found.

**AWS_REGION**

AWS region

required; string; AWS only

**AWS_ACCOUNT_ID**

AWS account id

required; string; AWS only

**AWS_ACCESS_KEY**

AWS access key

required; string; AWS only

**AWS_CONNECT_TIMEOUT_S**

AWS connection timeout

optional; int; default: 2; AWS only

**AWS_ENDPOINT_SNS**

AWS endpoint for SNS. This may be used to customized AWS endpoints to assist with testing, for example, using
localstack.

optional; string; AWS only

**AWS_ENDPOINT_SQS**

AWS endpoint for SQS. This may be used to customized AWS endpoints to assist with testing, for example, using
localstack.

optional; string; AWS only

**AWS_READ_TIMEOUT_S**

AWS read timeout

optional; int; default: 2; AWS only

**AWS_SECRET_KEY**

AWS secret key

required; string; AWS only

**AWS_SESSION_TOKEN**

AWS session token that represents temporary credentials (for example, for Lambda apps)

optional; string; AWS only

**GOOGLE_APPLICATION_CREDENTIALS**

Path to the Google application credentials json file

required; string; Google only

**GOOGLE_PUBSUB_PROJECT_ID**

Flag indicating if this is a Lambda app

required if Google Cloud Platform is used; string;

**GOOGLE_PUBSUB_READ_TIMEOUT_S**

Read from PubSub subscription timeout in seconds

optional: int; default: 5; Google only

**IS_LAMBDA_APP**

Flag indicating if this is a Lambda app

optional; string; default: False; AWS only

**TASKHAWK_CONSUMER_BACKEND**

Taskhawk consumer backend class

required; string

**TASKHAWK_DEFAULT_HEADERS**

A function that may be used to inject custom headers into every message, for example, request id. This hook is called
right before dispatch, and any headers that are explicitly specified when dispatching may override these headers.

If specified, it's called with the following arguments:

.. code:: python

  default_headers(task=task)

where ``task`` is the task function, and its expected to return a dict of strings.

It's recommended that this function be declared with ``**kwargs`` so it doesn't break on new versions of the library.

optional; fully-qualified function name

**TASKHAWK_GOOGLE_MESSAGE_RETRY_STATE_BACKEND**

Class to store task's retry state

optional; string; Google only

**TASKHAWK_GOOGLE_MESSAGE_RETRY_STATE_REDIS_URL**

required if ``MessageRetryStateRedis`` is used as task state retry backend; string; Google only

**TASKHAWK_GOOGLE_MESSAGE_MAX_RETRIES**

Number of task retries before moving message to dead letter queue (-DLQ)

optional; int; default: 3; Google only

**TASKHAWK_PRE_PROCESS_HOOK**

A function which can used to plug into the message processing pipeline *before* any processing happens. This hook
may be used to perform initializations such as set up a global request id based on message headers. If
specified, this will be called with the following arguments for AWS SQS apps:

.. code:: python

  pre_process_hook(queue_name=queue_name, sqs_queue_message=sqs_queue_message)

where ``sqs_queue_message`` is of type ``boto3.sqs.Message``.

For AWS Lambda apps as so:

.. code:: python

  pre_process_hook(sns_record=record)

where ``sns_record`` is a ``dict`` of a single record with format as described in lambda_sns_format_.

For Google apps as so:

.. code:: python

  pre_process_hook(google_pubsub_message=google_pubsub_message)

where ``google_pubsub_message`` is of type ``google.cloud.pubsub_v1.proto.pubsub_pb2.ReceivedMessage``.

It's recommended that this function be declared with ``**kwargs`` so it doesn't break on new versions of the library.

optional; fully-qualified function name

**TASKHAWK_POST_PROCESS_HOOK**

Same as ``TASKHAWK_PRE_PROCESS_HOOK`` but executed after task processing.

**TASKHAWK_PUBLISHER_BACKEND**

Taskhawk publisher backend class

required; string

**TASKHAWK_PUBLISHER_GCP_BATCH_SETTINGS**

Batching configuration for the ``GooglePubSubAsyncPublisherBackend`` publisher.

See `Google PubSub Docs`_ for more information.

**TASKHAWK_QUEUE**

The name of the taskhawk queue (exclude the ``TASKHAWK-`` prefix).

required; string

**TASKHAWK_SYNC**

Flag indicating if Taskhawk should work synchronously. This is similar to Celery's Eager mode and is helpful for
integration testing.

optional; bool; default False

**TASKHAWK_TASK_CLASS**

The name of a class to use as Task class rather than the default ``taskhawk.Task``. This may be used to customize the
behavior of tasks.

optional; fully-qualified class name


.. _lambda_sns_format: https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns
.. _Google PubSub Docs: https://google-cloud.readthedocs.io/en/latest/pubsub/types.html#google.cloud.pubsub_v1.types.BatchSettings