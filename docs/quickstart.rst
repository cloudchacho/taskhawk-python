Quickstart
==========

Getting started with Taskhawk is easy, but requires a few steps.


Installation
------------

Install the latest taskhawk release via *pip*:

.. code:: sh

   $ pip install taskhawk[aws]

If using Google, use ``taskhawk[gcp]``.

You may also install a specific version:

.. code:: sh

   $ pip install taskhawk[aws]==1.0.0

The latest development version can always be found on Github_.


Configuration
-------------

Before you can use Taskhawk, you need to set up a few settings. For Django projects, simple use `Django settings`_
to configure Taskhawk. For Flask projects, use `Flask config`_. For other frameworks, you can either declare an
environment variable called ``SETTINGS_MODULE`` that points to a module where settings may be found, or manually
configure using ``taskhawk.conf.settings.configure_with_object``.


There are 2 cloud platforms currently supported: AWS and Google Cloud Platform. Settings will defer depending on your
platform.

Common required settings:

.. code:: python

    TASKHAWK_QUEUE = <YOUR APP TASKHAWK QUEUE>


When using AWS, additional required settings are:

.. code:: python

    AWS_ACCESS_KEY = <YOUR AWS KEY>
    AWS_ACCOUNT_ID = <YOUR AWS ACCOUNT ID>
    AWS_REGION = <YOUR AWS REGION>
    AWS_SECRET_KEY = <YOUR AWS SECRET KEY>

    TASKHAWK_CONSUMER_BACKEND = 'taskhawk.backends.aws.AWSSQSConsumerBackend'
    TASKHAWK_PUBLISHER_BACKEND = 'taskhawk.backends.aws.AWSSNSPublisherBackend'


In case of GCP, additional required settings are:

.. code:: python

    TASKHAWK_CONSUMER_BACKEND = 'taskhawk.backends.gcp.GooglePubSubConsumerBackend'
    TASKHAWK_PUBLISHER_BACKEND = 'taskhawk.backends.gcp.GooglePubSubPublisherBackend'

If running outside Google Cloud (e.g. locally), set ``GOOGLE_APPLICATION_CREDENTIALS``.

Within Google Cloud, these credentials and permissions are managed by Google using IAM.

If the Pub/Sub resources lie in a different project, set ``GOOGLE_CLOUD_PROJECT`` to the project id.

For batch publish, use ``taskhawk.backends.gcp.GooglePubSubAsyncPublisherBackend``

Provisioning
------------

Taskhawk works on topics, queues, and subscriptions on AWS and Google cloud platforms.
Before you can publish tasks, you need to provision the required infra. This may be
done manually, or, preferably, using Terraform. Taskhawk provides tools to make infra
configuration easier: see `Taskhawk Terraform Generator`_ for further details.

Using Taskhawk
--------------

To use taskhawk, simply add the decorator :meth:`taskhawk.task` to your function:

.. code:: python

   @taskhawk.task
   def send_email(to: str, subject: str, from_email: str = None) -> None:
       # send email

And then dispatch your function asynchronously:

.. code:: python

    send_email.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')


Tasks are held in SQS queue, or Pub/Sub Subscription until they're successfully executed,
or until they fail a configurable number of times. Failed tasks are moved to a Dead
Letter Queue, where they're held for 14 days, and may be examined for further debugging.

Priority
--------

Taskhawk provides 4 priority queues to use, which may be customized per task, or per message.
For more details, see :class:`taskhawk.Priority`.

.. _Github: https://github.com/Automatic/taskhawk-python
.. _Django settings: https://docs.djangoproject.com/en/2.0/topics/settings/
.. _Flask config: https://flask.palletsprojects.com/en/1.1.x/config/
.. _Taskhawk Terraform Generator: https://github.com/Automatic/taskhawk-terraform-generator
