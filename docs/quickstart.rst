Quickstart
==========

Getting started with Taskhawk is easy, but requires a few steps.


Installation
------------

Install the latest taskhawk release via *pip*:

.. code:: sh

   $ pip install taskhawk

You may also install a specific version:

.. code:: sh

   $ pip install taskhawk==v1.0.0

The latest development version can always be found on Github_


Configuration
-------------

Before you can use Taskhawk, you need to set up a few settings. For Django projects,
simple use `Django settings`_ to configure Taskhawk, for non-Django projects, you
must declare an environment variable called ``SETTINGS_MODULE`` that points to a module
where settings may be found.

Required settings are:

.. code:: python

    AWS_ACCESS_KEY = <YOUR AWS KEY>
    AWS_ACCOUNT_ID = <YOUR AWS ACCOUNT ID>
    AWS_REGION = <YOUR AWS REGION>
    AWS_SECRET_KEY = <YOUR AWS SECRET KEY>

    TASKHAWK_QUEUE = <YOUR APP TASKHAWK QUEUE>


Provisioning
------------

Taskhawk works on SQS and SNS as backing queues. Before you can publish tasks, you
need to provision the required infra. This may be done manually, or, preferably,
using Terraform. Taskhawk provides tools to make infra configuration easier: see
Terraform_ and `Taskhawk Terraform Generator`_ for further details.

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


Tasks are held in SQS queue until they're successfully executed, or until they fail a
configurable number of times. Failed tasks are moved to a Dead Letter Queue, where they're
held for 14 days, and may be examined for further debugging.

Priority
--------

Taskhawk provides 4 priority queues to use, which may be customized per task, or per message.
For more details, see :class:`taskhawk.Priority`.

.. _Github: https://github.com/Automatic/taskhawk-python
.. _Django settings: https://docs.djangoproject.com/en/2.0/topics/settings/
.. _Terraform: https://github.com/Automatic/taskhawk-terraform
.. _Taskhawk Terraform Generator: https://github.com/Automatic/taskhawk-terraform-generator
