#!/bin/bash

set -e
set -x

PATH="$HOME:.local/bin:$PATH"

cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"

pyenv global 3.6.1
PYENV_ROOT="$(pyenv root)"
PIPENV_PYTHON="$PYENV_ROOT/shims/python"
export PYENV_ROOT PIPENV_PYTHON
pip install pipenv
pipenv install --dev
pipenv run make test
pipenv run make coverage-report
