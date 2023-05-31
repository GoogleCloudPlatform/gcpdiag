# Copyright 2023 Google LLC
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
"""Stub kubectl command execution for testing."""

import json
import pathlib

from gcpdiag.queries import kubectl


def check_gke_ingress(executor: kubectl.KubectlExecutor):
  filepath = pathlib.Path(__file__).parents[
      2] / 'test-data/gke1/json-dumps' / 'container-kubectl.json'
  with open(filepath, encoding='utf-8') as json_file:
    cluster_list = json.load(json_file)
    return json.dumps(cluster_list[executor.cluster.short_path]), None


def verify_auth(executor: kubectl.KubectlExecutor) -> bool:
  if executor.cluster.cluster_ca_certificate == 'REDACTED':
    return False
  return True
