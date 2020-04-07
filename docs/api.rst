API reference
=============

.. autodata:: taskhawk.conf.settings
    :annotation:

.. autofunction:: taskhawk.conf.settings.configure_with_object

.. autofunction:: taskhawk.conf.settings.clear_cache

.. attribute:: taskhawk.conf.settings.configured

   Have Taskhawk settings been configured?

.. module:: taskhawk

.. autofunction:: listen_for_messages
.. autofunction:: process_messages_for_lambda_consumer

.. autofunction:: task

.. autoclass:: Task
   :members: with_priority, with_headers, dispatch

.. autoclass:: Metadata
   :members: extend_visibility_timeout

.. autoclass:: Priority
   :members:
   :undoc-members:
   :member-order: bysource

.. autofunction:: requeue_dead_letter

.. autoclass:: GoogleMetadata
   :members: ack_id, publish_time, delivery_attempt
   :member-order: bysource

.. autoclass:: AWSMetadata
   :members: receipt
   :member-order: bysource

Exceptions
++++++++++

.. autoclass:: RetryException
.. autoclass:: LoggingException
.. autoclass:: IgnoreException
.. autoclass:: ValidationError
.. autoclass:: ConfigurationError
.. autoclass:: TaskNotFound
