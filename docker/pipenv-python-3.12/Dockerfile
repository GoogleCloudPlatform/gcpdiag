# Copyright 2024 Google LLC
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

# Python 3.12
FROM ubuntu:24.04

# Update apt-get and install required packages.
# binutils is for pyinstaller
RUN apt-get update && apt-get install --no-install-recommends -y \
	python3 \
	python3-pip \
	python3-dev \
	pipenv \
	curl \
	gnupg2 \
	binutils \
	make \
	git \
	bash \
	unzip \
	publicsuffix \
	build-essential


# terraform
RUN curl https://releases.hashicorp.com/terraform/1.9.6/terraform_1.9.6_openbsd_amd64.zip -O \
       && unzip -o *.zip -d /usr/bin/ terraform \
       && chmod +x /usr/bin/terraform \
       && rm *.zip

# gcloud CLI https://cloud.google.com/sdk/docs/install#installation_instructions
# We need the gcloud CLI to use this image as devcontainer, see: ../../.devcontainer/README.md
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg  add - && apt-get update -y && apt-get install google-cloud-cli -y

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]
