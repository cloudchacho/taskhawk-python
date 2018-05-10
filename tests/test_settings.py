import pytest

import taskhawk.conf


def test_fail_import_bad_value(settings):
    settings.TASKHAWK_DEFAULT_HEADERS = 'foo'

    with pytest.raises(ImportError):
        taskhawk.conf.settings.TASKHAWK_DEFAULT_HEADERS


def test_fail_import_bad_module(settings):
    settings.TASKHAWK_DEFAULT_HEADERS = 'foo.bar'

    with pytest.raises(ImportError):
        taskhawk.conf.settings.TASKHAWK_DEFAULT_HEADERS


def test_fail_import_bad_attr(settings):
    settings.TASKHAWK_DEFAULT_HEADERS = 'tests.tasks.foobar'

    with pytest.raises(ImportError):
        taskhawk.conf.settings.TASKHAWK_DEFAULT_HEADERS
