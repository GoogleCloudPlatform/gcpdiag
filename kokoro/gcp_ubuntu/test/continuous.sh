#!/bin/bash

set -e
set -x

PATH="${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor/bin:$HOME/.local/bin:$PATH"
cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"

pipenv-dockerized run pipenv install --dev
pipenv-dockerized run make test
pipenv-dockerized run make coverage-report
pipenv-dockerized run make publish-test
