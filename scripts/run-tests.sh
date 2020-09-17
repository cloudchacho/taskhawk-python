#!/usr/bin/env bash

set -ex

options="-v -s --strict --cov=taskhawk --cov-report=html --cov-report=term"

if [ -z "${target}" ]; then
    target="tests"
fi

options="${target} ${options}"

mypy taskhawk

# make sure taskhawk can be imported without SETTINGS_MODULE set
python3 -c 'import taskhawk'

python3 -b -m pytest -p no:taskhawk ${options}

black --check .

flake8

pip install -e .
make docs
