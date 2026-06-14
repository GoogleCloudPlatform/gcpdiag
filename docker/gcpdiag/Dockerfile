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
FROM ubuntu:24.04@sha256:a08e551cb33850e4740772b38217fc1796a66da2506d312abe51acda354ff061

# Update apt-get and install required packages.
RUN apt-get update && apt-get install --no-install-recommends -y \
	python3 \
	python3-pip \
	pipenv \
	curl \
	publicsuffix \
	gnupg2

# Add an entrypoint to create a user in /etc/passwd and /etc/group.
COPY entrypoint.sh /usr/bin/entrypoint.sh
RUN chmod 755 /usr/bin/entrypoint.sh; \
    chmod 666 /etc/passwd /etc/group
ENTRYPOINT ["/usr/bin/entrypoint.sh"]

# Install gcpdiag + dependencies.
COPY dist /opt/gcpdiag
RUN cd /opt/gcpdiag && env PIPENV_VENV_IN_PROJECT=1 pipenv install --ignore-pipfile

# Grant write permission to write kubeconfig file in the directory.
RUN chmod a+w /opt/gcpdiag

# Install Google Cloud CLI and google-cloud-sdk-gke-gcloud-auth-plugin.
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] http://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
RUN export CLOUD_SDK_VERSION="494.0.0" && \
    curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    tar xf google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    rm google-cloud-sdk-${CLOUD_SDK_VERSION}-linux-x86_64.tar.gz && \
    ln -s /google-cloud-sdk/bin/gcloud /usr/bin/gcloud && \
    gcloud config set component_manager/disable_update_check true && \
    gcloud components remove bq gsutil && \
    rm -rf \
      /google-cloud-sdk/platform/bundledpythonunix \
      /google-cloud-sdk/.install/.backup \
      /google-cloud-sdk/data/cli/*.json \
      /google-cloud-sdk/lib/googlecloudsdk/third_party/apis/*.json \
      /google-cloud-sdk/lib/third_party/botocore/data \
      /google-cloud-sdk/lib/googlecloudsdk/generated_clients/apis/compute \
      /google-cloud-sdk/lib/googlecloudsdk/generated_clients/apis/aiplatform

RUN apt-get update && apt-get install -y google-cloud-sdk-gke-gcloud-auth-plugin

# Install kubectl
RUN curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && chmod +x ./kubectl && mv ./kubectl /usr/local/bin

# Install kubectl check-gke-ingress
RUN ln -s /opt/gcpdiag/kubectl-check_gke_ingress /usr/local/bin/kubectl-check_gke_ingress
