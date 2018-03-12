#!/usr/bin/env bash

python setup.py sdist bdist_wheel

pip install -e .[publish]

twine upload dist/*
