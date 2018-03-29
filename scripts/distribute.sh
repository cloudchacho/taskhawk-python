#!/usr/bin/env bash

pip install pip-tools
pip-sync requirements/publish.txt

python setup.py sdist bdist_wheel

twine upload dist/*
