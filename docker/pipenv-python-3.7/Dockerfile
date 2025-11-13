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

FROM python:3.7-slim@sha256:b53f496ca43e5af6994f8e316cf03af31050bf7944e0e4a308ad86c001cf028b

# Copy the pinned requirements file from the root directory
COPY requirements.txt /tmp/requirements.txt

# Install from the file, ensuring all hashes match
RUN pip install --require-hashes -r /tmp/requirements.txt

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

# Note: we install Cloud SDK in the python-3.9 image because we
# use that image also for interactive development, but we don't need that
# for the python-3.7 image (and adding Cloud SDK considerably increases the
# image size).

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
