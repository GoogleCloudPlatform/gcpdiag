#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


set -e
set -x

PATH="${KOKORO_ARTIFACTS_DIR}/git/gcpdiag/bin:$HOME/.local/bin:$PATH"
cd "${KOKORO_ARTIFACTS_DIR}/git/gcpdiag"

pipenv-dockerized run pipenv install --dev
pipenv-dockerized run make test
pipenv-dockerized run make -C kokoro kokoro-build

docker login -u _json_key --password-stdin https://us-docker.pkg.dev \
  <"$KOKORO_KEYSTORE_DIR/76327_gcpdiag-repo-kokoro"
make -C docker/gcpdiag build
make -C docker/gcpdiag push
make -C gcpdiag_google_internal/docker build
make -C gcpdiag_google_internal/docker push

gcloud auth activate-service-account kokoro@gcp-doctor-repo.iam.gserviceaccount.com \
  --key-file="$KOKORO_KEYSTORE_DIR/76327_gcp-doctor-repo-kokoro"
make -C docker/gcpdiag update-default
make -C gcpdiag_google_internal/docker update-default
