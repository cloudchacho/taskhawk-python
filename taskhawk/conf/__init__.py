#!/usr/bin/env python
import logging
import os
import importlib
from copy import deepcopy

try:
    from django.conf import settings as django_settings
    from django.dispatch import receiver
    from django.test import signals

    HAVE_DJANGO = True
except ImportError:
    HAVE_DJANGO = False

try:
    from flask import current_app

    HAVE_FLASK = True
except ImportError:
    HAVE_FLASK = False


_DEFAULTS = {
    'AWS_REGION': None,
    'AWS_ACCOUNT_ID': None,
    'AWS_ACCESS_KEY': None,
    'AWS_CONNECT_TIMEOUT_S': 2,
    'AWS_ENDPOINT_SNS': None,
    'AWS_ENDPOINT_SQS': None,
    'AWS_READ_TIMEOUT_S': 2,
    'AWS_SECRET_KEY': None,
    'AWS_SESSION_TOKEN': None,
    'GOOGLE_APPLICATION_CREDENTIALS': None,
    'GOOGLE_CLOUD_PROJECT': None,
    'GOOGLE_PUBSUB_READ_TIMEOUT_S': 20,
    'IS_LAMBDA_APP': False,
    'TASKHAWK_CONSUMER_BACKEND': None,
    'TASKHAWK_DEFAULT_HEADERS': 'taskhawk.conf.default_headers_hook',
    'TASKHAWK_PRE_PROCESS_HOOK': 'taskhawk.conf.noop_hook',
    'TASKHAWK_POST_PROCESS_HOOK': 'taskhawk.conf.noop_hook',
    'TASKHAWK_PUBLISHER_BACKEND': None,
    'TASKHAWK_PUBLISHER_GCP_BATCH_SETTINGS': (),
    'TASKHAWK_QUEUE': None,
    'TASKHAWK_SYNC': False,
    'TASKHAWK_TASK_CLASS': 'taskhawk.task_manager.Task',
}


# List of settings that may be in string import notation.
_IMPORT_STRINGS = (
    'TASKHAWK_DEFAULT_HEADERS',
    'TASKHAWK_PRE_PROCESS_HOOK',
    'TASKHAWK_POST_PROCESS_HOOK',
    'TASKHAWK_TASK_CLASS',
)


def default_headers_hook(task, **kwargs):
    return {}


def noop_hook(*args, **kwargs):
    pass


class _LazySettings(object):
    """
    A settings object, that allows settings to be accessed as properties.
    For example:

    .. code-block:: python

        from taskhawk.conf import settings
        print(settings.AWS_REGION)

    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self):
        self._defaults = _DEFAULTS
        self._import_strings = _IMPORT_STRINGS
        self._user_settings: object = None

    @property
    def configured(self) -> bool:
        """
        Have Taskhawk settings been configured?
        """
        return bool(self._user_settings)

    def _ensure_configured(self):
        if self._user_settings:
            return

        if os.environ.get("SETTINGS_MODULE"):
            logging.info(f'Configuring Taskhawk through module: {os.environ["SETTINGS_MODULE"]}')
            self._user_settings = importlib.import_module(os.environ["SETTINGS_MODULE"], package=None)
        elif HAVE_DJANGO:
            # automatically import Django settings in Django projects
            logging.info('Configuring Taskhawk through django settings')
            self._user_settings = django_settings
        elif HAVE_FLASK:
            logging.info('Configuring Taskhawk through flask settings')
            # automatically import Flask settings in Flask projects
            self._user_settings = current_app.config
        if not self._user_settings:
            raise ImportError("Taskhawk settings have not been configured")

    def configure_with_object(self, obj: object) -> None:
        """
        Set Taskhawk config using a dataclass-like object that contains all settings as its attributes, or a dict that
        contains settings as its keys.
        """
        assert not self._user_settings, "settings have already been configured"

        logging.info('Configuring Taskhawk through object')
        self._user_settings = deepcopy(obj)

    @staticmethod
    def _import_string(dotted_path):
        """
        Import a dotted module path and return the attribute/class designated by the
        last name in the path. Raise ImportError if the import failed.
        """
        try:
            module_path, class_name = dotted_path.rsplit('.', 1)
        except ValueError as err:
            raise ImportError(f"{dotted_path} doesn't look like a module path") from err

        module = importlib.import_module(module_path)

        try:
            return getattr(module, class_name)
        except AttributeError as err:
            raise ImportError(f"Module '{module_path}' does not define a '{class_name}' attribute/class") from err

    def _get_setting_from_object(self, attr: str):
        if isinstance(self._user_settings, dict):
            if attr in self._user_settings:
                return self._user_settings[attr]
            elif attr.lower() in self._user_settings:
                return self._user_settings[attr.lower()]
            raise RuntimeError
        else:
            try:
                # Check if present in user settings
                return getattr(self._user_settings, attr)
            except AttributeError:
                # try lowercase
                try:
                    return getattr(self._user_settings, attr.lower())
                except AttributeError:
                    raise RuntimeError

    def __getattr__(self, attr):
        self._ensure_configured()

        if attr not in self._defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:
            val = self._get_setting_from_object(attr)
        except RuntimeError:
            # Fall back to defaults
            val = self._defaults[attr]

        # Coerce import strings into classes
        if attr in self._import_strings:
            val = self._import_string(val)

        # Cache the result
        setattr(self, attr, val)
        return val

    def clear_cache(self):
        """
        Clear settings cache - useful for testing only
        """
        for attr in self._defaults:
            try:
                delattr(self, attr)
            except AttributeError:
                pass


if HAVE_DJANGO:

    @receiver(signals.setting_changed)
    def clear_cache_on_setting_override(sender, setting, value, enter, **kwargs):
        settings.clear_cache()


settings = _LazySettings()
"""
This object allows settings to be accessed as properties. Settings can be configured in one of three ways:

#. Environment variable named ``SETTINGS_MODULE`` that points to a python module with settings as module attributes

#. Django - if Django can be imported, Django settings will be used automatically

#. Flask - if Flask can be imported, Flask current application's config will be used automatically

#. Using an object or dict, by calling :meth:`taskhawk.conf.settings.configure_with_object`

Some setting values need to be string import paths will be automatically resolved and return the class.

Once settings have been configured, they can't be changed.
"""


def configure_with_object(config: object) -> None:
    """
    Set Taskhawk config using a dataclass-like object that contains all settings as its attributes, or a dict that
    contains settings as its keys.
    """
    settings.configure_with_object(config)
