#!/bin/bash

set -e
set -x

PATH="${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor/bin:$HOME/.local/bin:$PATH"
cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"

pipenv-dockerized run pipenv install --dev
pipenv-dockerized run make test
pipenv-dockerized run make coverage-report
pipenv-dockerized run make kokoro-build

docker login -u _json_key --password-stdin https://us-docker.pkg.dev \
  <"$KOKORO_KEYSTORE_DIR/75985_gcp-doctor-repo-kokoro"
make -C docker/gcp-doctor build
make -C docker/gcp-doctor push
