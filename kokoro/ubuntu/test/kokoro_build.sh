#!/bin/bash

set -e

cd "${KOKORO_ARTIFACTS_DIR}/git/gcp-doctor"
./build.sh
