Configuration
=============

Add appropriate configuration to the app. If not using a Django app, ensure that `SETTINGS_MODULE` is
defined to the path of a module where all settings can be found.

**AWS_REGION**

AWS region

required; string

**AWS_ACCOUNT_ID**

AWS account id

required; string

**AWS_ACCESS_KEY**

AWS access key

required; string

**AWS_CONNECT_TIMEOUT_S**

AWS connection timeout

optional; int; default: 2

**AWS_READ_TIMEOUT_S**

AWS read timeout

optional; int; default: 2

**AWS_SECRET_KEY**

AWS secret key

required; string

**AWS_SESSION_TOKEN**

AWS session token that represents temporary credentials (for example, for Lambda apps)

optional; string

**IS_LAMBDA_APP**

Flag indicating if this is a Lambda app

optional; string; default: False

**TASKHAWK_DEFAULT_HEADERS**

A function that may be used to inject custom headers into every message, for example, request id. This hook is called
right before dispatch, and any headers that are explicitly specified when dispatching may override these headers.

If specified, it's called with the following arguments:

.. code:: python

  default_headers(task=task)

where ``task`` is the task function, and its expected to return a dict of strings.

It's recommended that this function be declared with ``**kwargs`` so it doesn't break on new versions of the library.

optional; fully-qualified function name

**TASKHAWK_MAX_DB_REUSE_LOOPS**

Number of loops before database connections are recycled. Only applies to Django apps.

optional; int; default: 5

**TASKHAWK_PRE_PROCESS_HOOK**

A function which can used to plug into the message processing pipeline //before// any processing happens. This hook
may be used to perform initializations such as set up a global request id based on message headers. If
specified, this will be called with the following arguments for SQS apps:

.. code:: python

  pre_process_hook(queue_name=queue_name, sqs_queue_message=sqs_queue_message)

where ``sqs_queue_message`` is of type ``boto3.sqs.Message``. And for Lambda apps as so:

.. code:: python

  pre_process_hook(sns_record=record)

where ``sns_record`` is a ``dict`` of a single record with format as described in lambda_sns_format_.

It's recommended that this function be declared with ``**kwargs`` so it doesn't break on new versions of the library.

optional; fully-qualified function name

**TASKHAWK_QUEUE**

The name of the taskhawk queue (exclude the ``TASKHAWK-`` prefix).

required; string

**TASKHAWK_SYNC**

Flag indicating if Taskhawk should work synchronously. This is similar to Celery's Eager mode and is helpful for
integration testing.

optional; default False

**TASKHAWK_TASK_CLASS**

The name of a class to use as Task class rather than the default ``taskhawk.Task``. This may be used to customize the
behavior of tasks.

optional; fully-qualified class name


.. _lambda_sns_format: https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns

