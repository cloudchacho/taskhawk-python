Taskhawk Migration Guide
========================

v1 → v2
~~~~~~~

Update your settings by setting consumer and publisher backends:

.. code:: python

    TASKHAWK_PUBLISHER_BACKEND = 'taskhawk.backends.aws.AWSSNSPublisherBackend'
    TASKHAWK_CONSUMER_BACKEND = 'taskhawk.backends.aws.AWSSQSConsumerBackend'

CELERY → v1
~~~~~~~~~~~~

Assuming publishers and workers are completely independent processes:

1. Remove all celery task decorators from your task functions and replace them with :meth:`taskhawk.task`.
#. Remove all celery related settings from your project.
#. Provision infra required for taskhawk using and taskhawk_terraform_generator_, or manually.
#. Add new processes for workers on each priority queue that your app publishes to (not all queues may be relevant
   for your app).
#. Deploy Taskhawk worker processes (not publishers).
#. Verify that Taskhawk workers pick up message by sending a test message.
#. Deploy publisher processes.
#. Let Celery queues drain to 0.
#. Terminate Celery worker processes.

If Celery workers also publish async tasks:

1. Remove all celery task decorators from your task functions and replace them with :meth:`taskhawk.task`.
#. Remove all celery related settings from your project.
#. Provision infra required for taskhawk using and taskhawk_terraform_generator_, or manually.
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


.. _taskhawk_terraform_generator: https://github.com/Automatic/taskhawk-terraform-generator
