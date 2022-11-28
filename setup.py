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
    'black',
    'coverage',
    'coveralls',
    'flake8',
    'ipdb',
    'moto',
    'mypy',
    'pytest',
    'pytest-cov',
    'pytest-env',
]

setup(
    name='taskhawk',
    version=version,
    description='Taskhawk Python Library',
    long_description=long_description,
    url='https://github.com/cloudchacho/taskhawk-python',
    author='Automatic Labs',
    license='Apache Software License (Apache License 2.0)',
    maintainer='Aniruddha Maru',
    maintainer_email='aniruddhamaru@gmail.com',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Natural Language :: English',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: Apache Software License',
    ],
    python_requires='>=3.6',
    keywords='python taskhawk',
    # https://mypy.readthedocs.io/en/latest/installed_packages.html
    package_data={'taskhawk': ['py.typed']},
    packages=find_packages(exclude=['contrib', 'docs', 'tests', 'tests.*']),
    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['funcy', 'arrow', 'dataclasses; python_version<"3.7"'],
    tests_require=tests_require,
    setup_requires=['pytest-runner'],
    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'aws': ['boto3', 'retrying'],
        'gcp': ['google-cloud-pubsub>=2.0.0', 'grpcio-status==1.48.2'],
        'dev': [
            'flake8',
            'docutils<0.18; python_version < "3.8"',
            'Sphinx==3.2.1; python_version < "3.8"',
            'Sphinx>3; python_version >= "3.8"',
            'jinja2<3.1; python_version >= "3.7" and python_version < "3.8"',
            'pip-tools',
            'wheel',
            'boto3-stubs[sns,sqs]',
            'types-dataclasses',
        ],
        'test': tests_require,
        'publish': ['bumpversion', 'twine'],
    },
    include_package_data=True,
)
