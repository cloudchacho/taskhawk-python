Taskhawk Library for Python
===========================

.. image:: https://travis-ci.org/Automatic/taskhawk-python.svg?branch=master
    :target: https://travis-ci.org/Automatic/taskhawk-python

.. image:: https://coveralls.io/repos/github/Automatic/taskhawk-python/badge.svg?branch=master
    :target: https://coveralls.io/github/Automatic/taskhawk-python?branch=master

.. image:: https://img.shields.io/pypi/v/taskhawk.svg?style=flat-square
    :target: https://pypi.python.org/pypi/taskhawk

.. image:: https://img.shields.io/pypi/pyversions/taskhawk.svg?style=flat-square
    :target: https://pypi.python.org/pypi/taskhawk

.. image:: https://img.shields.io/pypi/implementation/taskhawk.svg?style=flat-square
    :target: https://pypi.python.org/pypi/taskhawk

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black

TaskHawk is a replacement for celery that works on AWS SQS/SNS and Google PubSub, while keeping things pretty simple and
straightforward. Any unbound function can be converted into a TaskHawk task.

Only Python 3.6+ is supported currently.

You can find the latest, most up to date, documentation at `Read the Docs`_.


Quick Start
-----------

First, install the library:

.. code:: sh

    $ pip install taskhawk

Next, set up a few configuration settings:

Common required settings:

.. code:: python

    TASKHAWK_QUEUE = "DEV-MYAPP"

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

For Django projects, simple use `Django settings`_ to configure Taskhawk. For Flask projects, use `Flask config`_.
For other frameworks, you can either declare an environment variable called ``SETTINGS_MODULE`` that points to a
module where settings may be found, or manually configure using ``taskhawk.conf.settings.configure_with_object``.

Then, simply add the decorator ``taskhawk.task`` to your function:

.. code:: python

   @taskhawk.task
   def send_email(to: str, subject: str, from_email: str = None) -> None:
       # send email

And finally, dispatch your function asynchronously:

.. code:: python

    send_email.dispatch('example@email.com', 'Hello!', from_email='example@spammer.com')

Development
-----------

Getting Started
~~~~~~~~~~~~~~~
Assuming that you have Python, ``pyenv`` and ``pyenv-virtualenv`` installed, set up your
environment and install the required dependencies like this instead of
the ``pip install taskhawk`` defined above:

.. code:: sh

    $ git clone https://github.com/Automatic/taskhawk-python.git
    $ cd taskhawk-python
    $ pyenv virtualenv 3.6.5 taskhawk-3.6
    ...
    $ pyenv activate taskhawk-3.6
    $ pip install -r requirements/dev-3.6.txt

Running Tests
~~~~~~~~~~~~~
You can run tests in using ``make test``. By default,
it will run all of the unit and functional tests, but you can also specify your own
``py.test`` options.

.. code:: sh

    $ py.test
    $ py.test tests/test_consumer.py

Generating Documentation
~~~~~~~~~~~~~~~~~~~~~~~~
Sphinx is used for documentation. You can generate HTML locally with the
following:

.. code:: sh

    $ pip install -e .[dev]
    $ make docs


Getting Help
------------

We use GitHub issues for tracking bugs and feature requests.

* If it turns out that you may have found a bug, please `open an issue <https://github.com/Automatic/taskhawk-python/issues/new>`__

.. _Read the Docs: https://taskhawk.readthedocs.io/en/latest/
.. _Django settings: https://docs.djangoproject.com/en/2.0/topics/settings/
.. _Flask config: https://flask.palletsprojects.com/en/1.1.x/config/
