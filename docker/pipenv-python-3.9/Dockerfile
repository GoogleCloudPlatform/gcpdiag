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

FROM python:3.9-slim@sha256:914169c7c8398b1b90c0b0ff921c8027445e39d7c25dc440337e56ce0f2566e6

# Add pipenv.
RUN pip install pipenv

# Debian packages.
# binutils is for pyinstaller
RUN apt-get update && \
    apt-get -y install \
        bash \
        curl \
        git \
        gnupg \
        binutils \
        make

# terraform
RUN curl https://releases.hashicorp.com/terraform/1.0.8/terraform_1.0.8_linux_amd64.zip | \
    gunzip - >/usr/bin/terraform && \
    chmod +x /usr/bin/terraform

# gcloud CLI https://cloud.google.com/sdk/docs/install#installation_instructions
# We need the gcloud CLI to use this image as devcontainer, see: ../../.devcontainer/README.md
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
