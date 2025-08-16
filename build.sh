#!/usr/bin/env bash
# Exit on error
set -o errexit

# Modify this line to specify the Python version you want
PYTHON_VERSION=3.12.13

# Install the specified Python version
pyenv install $PYTHON_VERSION --skip-existing
pyenv global $PYTHON_VERSION

# Install dependencies
pip install -r requirements.txt