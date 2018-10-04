#!/usr/bin/env bash

set -e

options="-v -s --strict --cov=taskhawk"

if [ -z "${target}" ]; then
    target="tests"
fi

options="${target} ${options}"

mypy taskhawk

python3 -bb -m pytest ${options}

black --skip-string-normalization --skip-numeric-underscore-normalization --line-length=120 --check .

flake8

pip install -e .
make docs
