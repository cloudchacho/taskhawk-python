===============
TaskHawk Python
===============

TaskHawk is a replacement for celery that works on AWS SQS/SNS, while keeping things pretty simple and straight
forward Any unbound function can be converted into a TaskHawk task.

Only Python 3.6+ is supported currently.

This project uses `semantic versioning
<http://semver.org/>`_.

Usage
-----

Add ``taskhawk`` to ``requirements/base.in`` file and compile requirements. Add appropriate configuration to the app.
If not using a Django app, ensure that ``SETTINGS_MODULE`` is defined to the path of a module where all settings can
be found.

**TASKS**

Add ``@taskhawk.task`` decorator to convert any unbound function into an async task, as shown here:

.. code:: python

   @taskhawk.task
   def send_email(to: str, subject: str, from_email: str = None) -> None:
       # send email

Optionally, pass in ``priority=taskhawk.Priority.high`` to mark the task as a high priority task.

If your task function accepts an kwarg called ``metadata`` (of type ``dict``) or ``**kwargs``, the function will be
called with a ``metadata`` parameter as a dict with the following attributes:

**id**: task identifier. This represents a run of a task.

**version**: message format version. Currently can only be 1.

**timestamp**: task dispatch epoch timestamp (milli-seconds)

**receipt**: SQS receipt for the task. This may be used to extend message visibility if the task is running longer
than expected.

If your task function accepts an kwarg called ``headers`` (of type ``dict``) or ``**kwargs``, the function will be
called with a ``headers`` parameter which is dict that the task was dispatched with.

**PUBLISHER**

You can run tasks asynchronously like so:

.. code:: python

  send_email.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

If you want to include a custom headers with the message (for example, you can include a ``request_id`` field for
cross-application tracing), or you want to customize priority, you can customize a particular task invocation using
chaining like so:

.. code:: python

  tasks.send_email.with_headers(request_id='1234').with_priority(taskhawk.Priority.high).dispatch('example@email.com')

**CONSUMER**

A consumer for SQS based workers can be started as following:

.. code:: python

  taskhawk.listen_for_messages(taskhawk.Priority.high)

This is a blocking function, so if you want to listen to multiple priority queues, you'll need to run these on
separate processes (don't use threads since this library isn't guaranteed to be thread-safe).

A consumer for Lambda based workers can be started as following:

.. code:: python

  taskhawk.process_messages_for_lambda_consumer(lambda_event)

where ``lambda_event`` is the event provided by AWS to your Lambda function as described `here
<https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns>`_.

Settings
--------

**AWS_REGION**

AWS region

required; string

**AWS_ACCOUNT_ID**

AWS account id (ask @ops if unsure)

required; string

**AWS_ACCESS_KEY**

AWS access key (ask @ops if you don't have one)

required; string

**AWS_CONNECT_TIMEOUT_S**

AWS connection timeout

optional; int; default: 2

**AWS_READ_TIMEOUT_S**

AWS read timeout

optional; int; default: 2

**AWS_SECRET_KEY**

AWS secret key (ask @ops if you don't have one)

required; string

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

How to release
--------------

1. Edit code, get it code reviewed, and land it
#. Edit ``README.rst``:

   - Update ``Release notes`` - add a new section for the version you're going to release, and create an empty
     ``unreleased`` section
   - Update ``Migration guide`` if applicable.

3. Push changes
#. Execute https://jenkins.automatic.co/job/taskhawk-python-RELEASE/ with appropriate params (contact an admin if you
   don't have permissions).
#. Verify new version was uploaded successfully here: https://pypi.automatic.co/#/package/taskhawk
#. Publish Github Release: https://github.com/Automatic/taskhawk-python/releases/

Release notes
-------------

**Current version: v1.0.0**

v1.0.0
~~~~~~

- Initial version

Migration guide
---------------

Since this is now a library rather than subtree, migration is much simpler. Simply run ``make vupgrade_requirement
pkg=taskhawk`` to update requirement files. If migrating across major/minor versions, check below for any specific
steps needed.

CELERY -> v1.0.0
~~~~~~~~~~~~~~~~

Assuming publishers and workers are completely independent processes:

1. Remove all celery task decorators from your task functions and replace them with ``@taskhawk.task``.
#. Remove all celery related settings from your project.
#. Provision infra required for taskhawk using taskhawk_terraform_ and taskhawk_terraform_generator_, or manually.
#. Add new processes for workers on each priority queue that your app publishes to (not all queues may be relevant
   for your app).
#. Deploy Taskhawk worker processes (not publishers).
#. Verify that Taskhawk workers pick up message by sending a test message.
#. Deploy publisher processes.
#. Let Celery queues drain to 0.
#. Terminate Celery worker processes.

If Celery workers also publish async tasks:

1. Remove all celery task decorators from your task functions and replace them with ``@taskhawk.task``.
#. Remove all celery related settings from your project.
#. Provision infra required for taskhawk using taskhawk_terraform_ and taskhawk_terraform_generator_, or manually.
#. Add new processes for workers on each priority queue that your app publishes to (not all queues may be relevant
   for your app).
#. Deploy a test TaskHawk worker process.
#. Verify that Taskhawk workers pick up message by sending a test message.
#. Double publish to both Taskhawk and Celery in Celery workers.
#. Deploy Taskhawk worker processes (not other publishers).
#. Deploy other publisher processes.
#. Remove double publish in Celery workers.
#. Deploy Celery workers.
#. Let Celery queues drain to 0.
#. Terminate Celery worker processes.


.. _lambda_sns_format: https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns
.. _taskhawk_terraform: https://github.com/Automatic/taskhawk-terraform
.. _taskhawk_terraform_generator: https://github.com/Automatic/taskhawk-terraform-generator
