Taskhawk documentation
======================

TaskHawk is a replacement for celery that works on AWS SQS/SNS, while keeping things pretty simple and straight
forward. Any unbound function can be converted into a TaskHawk task.

For inter-service messaging, see Hedwig_.

Only Python 3.6+ is supported currently.

This project uses `semantic versioning
<http://semver.org/>`_.

Quickstart
----------

.. toctree::
   :maxdepth: 2

   quickstart

Usage
-----
.. toctree::
   usage
   settings
   api
   releases
   migration


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Hedwig: http://hedwig.rtfd.io/
