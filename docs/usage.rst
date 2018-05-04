Usage Guide
===========

Tasks
+++++

Add :meth:`taskhawk.task` decorator to convert any unbound function into an async task, as shown here:

.. code:: python

   @taskhawk.task
   def send_email(to: str, subject: str, from_email: str = None) -> None:
       # send email

Optionally, pass in ``priority=taskhawk.Priority.high`` to mark the task as a high priority task.

Task name is automatically inferred from decorated function module and name, but you can also set it
explicitly with ``name`` parameter.

If your task function accepts an kwarg called ``metadata`` (of type ``dict``) or ``**kwargs``, the function will be
called with a ``metadata`` parameter as a dict with the following attributes:

**id**: task identifier. This represents a run of a task.

**priority**: the priority a task was dispatched with. This will be same as task's priority, unless priority was
customized on dispatch.

**receipt**: SQS receipt for the task. This may be used to extend message visibility if the task is running longer
than expected using ``taskhawk.extend_visibility_timeout``.

**timestamp**: task dispatch epoch timestamp (milliseconds)

**version**: message format version. Currently can only be 1.

If your task function accepts an kwarg called ``headers`` (of type ``dict``) or ``**kwargs``, the function will be
called with a ``headers`` parameter which is dict that the task was dispatched with.

Publisher
+++++++++

You can run tasks asynchronously like so:

.. code:: python

  send_email.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

If you want to include a custom headers with the message (for example, you can include a ``request_id`` field for
cross-application tracing), or you want to customize priority, you can customize a particular task invocation using
chaining like so:

.. code:: python

  send_email.with_headers(request_id='1234')\
            .with_priority(taskhawk.Priority.high)\
            .dispatch('example@email.com')

Consumer
++++++++

A consumer for SQS based workers can be started as following:

.. code:: python

  taskhawk.listen_for_messages(taskhawk.Priority.high)

This is a blocking function, so if you want to listen to multiple priority queues, you'll need to run these on
separate processes (don't use threads since this library is **NOT** guaranteed to be thread-safe).

A consumer for Lambda based workers can be started as following:

.. code:: python

  taskhawk.process_messages_for_lambda_consumer(lambda_event)

where ``lambda_event`` is the event provided by AWS to your Lambda function as described `here
<https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns>`_.

If your tasks exist in different modules, ensure that your modules are imported before calling Taskhawk listener
functions since tasks need to be registered before they can receive messages.

Internals
+++++++++

Message format
~~~~~~~~~~~~~~

Internally, all tasks are converted into a message that looks like this:

.. code:: json

    {
        "id": "b1328174-a21c-43d3-b303-964dfcc76efc",
        "metadata": {
            "priority": "high",
            "timestamp": 1460868253255,
            "version": "1.0"
        },
        "headers": {
            ...
        },
        "task": "tasks.send_email",
        "args": [
            "email@automatic.com",
            "Hello!"
        ],
        "kwargs": {
            "from_email": "spam@example.com"
        }
    }


.. _lambda_sns_format: https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns
.. _taskhawk_terraform_generator: https://github.com/Automatic/taskhawk-terraform-generator

