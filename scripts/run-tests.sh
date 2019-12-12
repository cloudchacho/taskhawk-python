#!/usr/bin/env bash

set -e

# https://github.com/travis-ci/travis-ci/issues/7940
export BOTO_CONFIG=/dev/null

options="-v -s --strict --cov=taskhawk --cov-report=html --cov-report=term"

if [ -z "${target}" ]; then
    target="tests"
fi

options="${target} ${options}"

mypy taskhawk

python3 -m pytest ${options}

black --skip-string-normalization --line-length=120 --check .

flake8

pip install -e .
make docs
