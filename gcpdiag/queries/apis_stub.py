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

import copy
import json
import pathlib
import re
from typing import Optional

import googleapiclient.errors

from gcpdiag.queries import (apigee_stub, composer_stub, crm_stub,
                             dataproc_stub, gce_stub, gcf_stub, gke_stub,
                             iam_stub, kms_stub, logs_stub, monitoring_stub)

# pylint: disable=unused-argument

JSON_PROJECT_DIR = {
    'gcpdiag-gce1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    '12340001':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    'gcpdiag-gke1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
    '12340002':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
    'gcpd-gcf1-s6ew':
        pathlib.Path(__file__).parents[2] / 'test-data/gcf1/json-dumps',
    'dataproc1':
        pathlib.Path(__file__).parents[2] / 'test-data/dataproc1/json-dumps',
    'gcpd-apigee-1-lus4':
        pathlib.Path(__file__).parents[2] / 'test-data/apigee1/json-dumps',
    'composer1':
        pathlib.Path(__file__).parents[2] / 'test-data/composer1/json-dumps',
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
    with open(self.json_dir / 'services.json', encoding='utf-8') as json_file:
      return json.load(json_file)


class BatchRequestStub:
  """Mock object returned by new_batch_http_request()."""

  def __init__(self, callback=None):
    self.queue = []
    self.callback = callback

  def add(self, request, callback=None, request_id=None):
    self.queue.append({
        'request': copy.deepcopy(request),
        'cb': callback or self.callback,
        'request_id': request_id
    })
    return self

  def execute(self):
    for op in self.queue:
      try:
        response = op['request'].execute()
        op['cb'](op['request_id'], response, None)
      except googleapiclient.errors.HttpError as err:
        op['cb'](op['request_id'], None, err)


def get_api_stub(service_name: str,
                 version: str,
                 project_id: Optional[str] = None):
  if service_name == 'cloudresourcemanager':
    return crm_stub.CrmApiStub()
  elif service_name == 'container':
    return gke_stub.ContainerApiStub()
  elif service_name == 'cloudkms':
    return kms_stub.KmsApiStub()
  elif service_name == 'compute':
    return gce_stub.ComputeEngineApiStub()
  elif service_name == 'iam':
    return iam_stub.IamApiStub()
  elif service_name == 'logging':
    return logs_stub.LoggingApiStub()
  elif service_name == 'monitoring':
    return monitoring_stub.MonitoringApiStub()
  elif service_name == 'serviceusage':
    return ServiceUsageApiStub()
  elif service_name == 'cloudfunctions':
    return gcf_stub.CloudFunctionsApiStub()
  elif service_name == 'dataproc':
    return dataproc_stub.DataprocApiStub()
  elif service_name == 'apigee':
    return apigee_stub.ApigeeApiStub()
  elif service_name == 'composer':
    return composer_stub.ComposerApiStub()
  else:
    raise ValueError('unsupported service: %s' % service_name)
