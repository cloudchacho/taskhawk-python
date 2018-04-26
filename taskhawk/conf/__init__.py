#!/usr/bin/env python

import os
import importlib


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
    'IS_LAMBDA_APP': False,
    'TASKHAWK_DEFAULT_HEADERS': 'taskhawk.conf.default_headers_hook',
    'TASKHAWK_MAX_DB_REUSE_LOOPS': 5,
    'TASKHAWK_PRE_PROCESS_HOOK': 'taskhawk.conf.noop_hook',
    'TASKHAWK_QUEUE': None,
    'TASKHAWK_SYNC': False,
    'TASKHAWK_TASK_CLASS': 'taskhawk.task_manager.Task',
}


# List of settings that may be in string import notation.
_IMPORT_STRINGS = (
    'TASKHAWK_DEFAULT_HEADERS',
    'TASKHAWK_PRE_PROCESS_HOOK',
    'TASKHAWK_TASK_CLASS',
)


def default_headers_hook():
    return {}


def noop_hook(*args, **kwargs):
    pass


class _LazySettings(object):
    """
    A settings object, that allows settings to be accessed as properties.
    For example:
        from taskhawk.conf import settings
        print(settings.AWS_REGION)
    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """
    def __init__(self):
        self._defaults = _DEFAULTS
        self._import_strings = _IMPORT_STRINGS
        self._user_settings = None

        if os.environ.get("SETTINGS_MODULE"):
            self._user_settings = importlib.import_module(os.environ["SETTINGS_MODULE"], package=None)
        else:
            # automatically import Django settings in Django projects
            try:
                from django.conf import settings as django_settings
                self._user_settings = django_settings
            except ImportError:
                pass
            if not self._user_settings:
                raise ImportError("No settings module found to import")

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

    def __getattr__(self, attr):
        if attr not in self._defaults:
            raise AttributeError("Invalid API setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = getattr(self._user_settings, attr)
        except AttributeError:
            # Fall back to defaults
            val = self._defaults[attr]

        # Coerce import strings into classes
        if attr in self._import_strings:
            val = self._import_string(val)

        # Cache the result
        setattr(self, attr, val)
        return val

    def clear_cache(self):
        for attr in self._defaults:
            try:
                delattr(self, attr)
            except AttributeError:
                pass


settings = _LazySettings()
