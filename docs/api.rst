API reference
=============

.. module:: taskhawk

.. autofunction:: listen_for_messages
.. autofunction:: process_messages_for_lambda_consumer

.. autofunction:: task

.. autoclass:: Task
   :members: with_priority, with_headers, dispatch

.. autoclass:: Priority
   :members:
   :undoc-members:
   :member-order: bysource

.. autofunction:: requeue_dead_letter, extend_visibility_timeout

Exceptions
++++++++++

.. autoclass:: RetryException
.. autoclass:: LoggingException
.. autoclass:: IgnoreException
.. autoclass:: ValidationError
.. autoclass:: ConfigurationError
.. autoclass:: TaskNotFound
