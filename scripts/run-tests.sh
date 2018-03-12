#!/usr/bin/env bash

set -e

exit_cleanup() {
    echo
}

err_cleanup() {
    echo
}

trap err_cleanup ERR

trap exit_cleanup EXIT

source ./scripts/venv-setup.sh

if [ -z "${fast}" ]; then
    pip install -e.[dev,test]
fi

options="-v -s --strict"

if [ -z "${target}" ]; then
    target="tests"
fi

options="${target} ${options}"

PYTHONWARNINGS=all py.test ${options}
