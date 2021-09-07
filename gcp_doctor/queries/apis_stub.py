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
"""Stub API calls used in apis.py for testing."""

import json
import pathlib
import re

from gcp_doctor.queries import crm_stub, gce_stub, gke_stub, iam_stub

# pylint: disable=unused-argument

JSON_PROJECT_DIR = {
    'gcpd-gce1-4exv':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    '50670056743':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    'gcpd-gke-1-9b90':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
    '18404348413':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
}


def get_json_dir(project_id: str):
  return JSON_PROJECT_DIR[project_id]


class ServiceUsageApiStub:
  """Mock object to simulate api calls."""

  def services(self):
    return self

  # pylint: disable=redefined-builtin
  def list(self, parent, filter):
    m = re.match(r'projects/([^/]+)', parent)
    project_id = m.group(1)
    self.json_dir = get_json_dir(project_id)
    return self

  def list_next(self, request, response):
    return None

  def execute(self, num_retries=0):
    with open(self.json_dir / 'services.json') as json_file:
      return json.load(json_file)


def get_api_stub(service_name: str, version: str, project_id: str):
  if service_name == 'cloudresourcemanager':
    return crm_stub.CrmApiStub()
  elif service_name == 'container':
    return gke_stub.ContainerApiStub()
  elif service_name == 'compute':
    return gce_stub.ComputeEngineApiStub()
  elif service_name == 'iam':
    return iam_stub.IamApiStub()
  elif service_name == 'serviceusage':
    return ServiceUsageApiStub()
  else:
    raise ValueError('unsupported service: %s' % service_name)
