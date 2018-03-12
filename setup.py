"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

import ast
from codecs import open
from os import path
import re
from setuptools import setup, find_packages


cwd = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(cwd, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

_version_re = re.compile(r'VERSION\s+=\s+(.*)')

with open('taskhawk/__init__.py', 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode('utf-8')).group(1)))

tests_require = [
    'pytest', 'flake8', 'pytest-env', 'ipdb'
]

setup(
    name='taskhawk',

    version=version,

    description='Taskhawk Python Library',
    long_description=long_description,

    url='https://github.com/Automatic/taskhawk-python',

    author='Automatic Labs',
    author_email='server-team@automatic.com',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project?
        'Development Status :: 5 - Production',

        # Indicate who your project is intended for
        'Intended Audience :: Automatic Developers',
        'Topic :: Software Development :: Build Tools',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.6',
    ],

    keywords='python taskhawk',

    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'tests.*']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['funcy', 'retrying', 'boto3', 'raven>=6.4.0'],

    tests_require=tests_require,

    setup_requires=[
        'pytest-runner'
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['flake8'],
        'test': tests_require,
        'publish': ['bumpversion', 'twine'],
    },

    include_package_data=True,
)
