#!/bin/bash

set -e
set -x

pyenv global 3.6.1

cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"
./build.sh
