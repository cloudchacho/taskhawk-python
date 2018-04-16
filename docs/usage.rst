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

If your task function accepts an kwarg called ``metadata`` (of type ``dict``) or ``**kwargs``, the function will be
called with a ``metadata`` parameter as a dict with the following attributes:

**id**: task identifier. This represents a run of a task.

**version**: message format version. Currently can only be 1.

**timestamp**: task dispatch epoch timestamp (milliseconds)

**receipt**: SQS receipt for the task. This may be used to extend message visibility if the task is running longer
than expected.

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
separate processes (don't use threads since this library isn't guaranteed to be thread-safe).

A consumer for Lambda based workers can be started as following:

.. code:: python

  taskhawk.process_messages_for_lambda_consumer(lambda_event)

where ``lambda_event`` is the event provided by AWS to your Lambda function as described `here
<https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns>`_.


.. _lambda_sns_format: https://docs.aws.amazon.com/lambda/latest/dg/eventsources.html#eventsources-sns
.. _taskhawk_terraform: https://github.com/Automatic/taskhawk-terraform
.. _taskhawk_terraform_generator: https://github.com/Automatic/taskhawk-terraform-generator

