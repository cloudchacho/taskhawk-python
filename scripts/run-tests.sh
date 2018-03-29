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

if [[ -z "${PYTHON_VERSIONS}" ]]; then
    echo "Unspecified PYTHON_VERSIONS, cannot proceed"
    exit 1
fi

PYTHON_VERSIONS_ARRAY=$(echo $PYTHON_VERSIONS | tr "," "\n")
for PYTHON_VERSION in $PYTHON_VERSIONS_ARRAY; do
    source ./scripts/venv-setup.sh

    if [ -z "${fast}" ]; then
        pip install pip-tools

        python_major_version=$(echo ${PYTHON_VERSION} | cut -f1 -d'.')
        python_minor_version=$(echo ${PYTHON_VERSION} | cut -f2 -d'.')
        pip-sync requirements/test-${python_major_version}.${python_minor_version}.txt
    fi

    options="-v -s --strict"

    if [ -z "${target}" ]; then
        target="tests"
    fi

    options="${target} ${options}"

    python3 -bb -m pytest ${options}
done
