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
from typing import Optional

import googleapiclient.errors
import httplib2

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
    'gcpdiag-gcf1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gcf1/json-dumps',
    'gcpdiag-gcs1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gcs1/json-dumps',
    'dataproc1':
        pathlib.Path(__file__).parents[2] / 'test-data/dataproc1/json-dumps',
    'gcpd-apigee-1-lus4':
        pathlib.Path(__file__).parents[2] / 'test-data/apigee1/json-dumps',
    'composer1':
        pathlib.Path(__file__).parents[2] / 'test-data/composer1/json-dumps',
    'gcpdiag-fw-policy-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/fw-policy/json-dumps',
    '12340004':
        pathlib.Path(__file__).parents[2] / 'test-data/fw-policy/json-dumps',
    'gcpdiag-cloudbuild1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudbuild1/json-dumps',
    'gcpdiag-pubsub1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/pubsub1/json-dumps',
    'gcpdiag-gaes1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gaes1/json-dumps'
}

# set to a value higher than 0 to emulate API temp. failure
fail_next_execute_count = 0


def get_json_dir(project_id: str):
  return JSON_PROJECT_DIR[project_id]


class ApiStub:
  """Base class for "API Stubs", i.e. objects that mock what is returned
  by the googleapiclient modules. This base class makes it easier to
  implement testing of failure modes on API failures thanks to the
  fail_next() and _maybe_raise_api_exception() methods."""

  _fail_count: int = 0

  def fail_next(self, fail_count: int, fail_status: int = 429):
    self._fail_count = fail_count
    self._fail_status = fail_status

  def _maybe_raise_api_exception(self):
    """Simulate API errors by possibly raising an exception, if
    fail_next() was called before to do that.

    Raises: googleapiclient.errors.HttpError exception."""

    if self._fail_count > 0:
      self._fail_count -= 1
      raise googleapiclient.errors.HttpError(
          httplib2.Response({'status': self._fail_status}),
          b'mocking API error')


class ServiceUsageApiStub(ApiStub):
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
    self._maybe_raise_api_exception()
    with open(self.json_dir / 'services.json', encoding='utf-8') as json_file:
      return json.load(json_file)


def _batch_request_default_callback(req_id, response, exception):
  """Make sure we catch when there is no callback defined."""
  raise RuntimeError(f'no callback defined for request {req_id}!')


class BatchRequestStub(ApiStub):
  """Mock object returned by new_batch_http_request()."""

  def __init__(self, callback=_batch_request_default_callback):
    self.queue = []
    self.callback = callback

  def add(self, request, callback=None, request_id=None):
    self.queue.append({
        'request': request,
        'cb': callback or self.callback,
        'request_id': request_id
    })
    return self

  def execute(self):
    self._maybe_raise_api_exception()

    for op in self.queue:
      try:
        response = op['request'].execute()
        op['cb'](op['request_id'], response, None)
      except googleapiclient.errors.HttpError as err:
        op['cb'](op['request_id'], None, err)


def get_api_stub(service_name: str,
                 version: str,
                 project_id: Optional[str] = None):

  # Avoid circular import dependencies by importing the required modules here.
  # pylint: disable=import-outside-toplevel

  if service_name == 'cloudresourcemanager':
    from gcpdiag.queries import crm_stub
    return crm_stub.CrmApiStub()
  elif service_name == 'container':
    from gcpdiag.queries import gke_stub
    return gke_stub.ContainerApiStub()
  elif service_name == 'cloudkms':
    from gcpdiag.queries import kms_stub
    return kms_stub.KmsApiStub()
  elif service_name == 'compute':
    from gcpdiag.queries import gce_stub
    return gce_stub.ComputeEngineApiStub()
  elif service_name == 'iam':
    from gcpdiag.queries import iam_stub
    return iam_stub.IamApiStub()
  elif service_name == 'logging':
    from gcpdiag.queries import logs_stub
    return logs_stub.LoggingApiStub()
  elif service_name == 'monitoring':
    from gcpdiag.queries import monitoring_stub
    return monitoring_stub.MonitoringApiStub()
  elif service_name == 'serviceusage':
    return ServiceUsageApiStub()
  elif service_name == 'cloudfunctions':
    from gcpdiag.queries import gcf_stub
    return gcf_stub.CloudFunctionsApiStub()
  elif service_name == 'dataproc':
    from gcpdiag.queries import dataproc_stub
    return dataproc_stub.DataprocApiStub()
  elif service_name == 'apigee':
    from gcpdiag.queries import apigee_stub
    return apigee_stub.ApigeeApiStub()
  elif service_name == 'composer':
    from gcpdiag.queries import composer_stub
    return composer_stub.ComposerApiStub()
  elif service_name == 'storage':
    from gcpdiag.queries import gcs_stub
    return gcs_stub.BucketApiStub()
  elif service_name == 'cloudbuild':
    from gcpdiag.queries import gcb_stub
    return gcb_stub.CloudBuildApiStub()
  elif service_name == 'pubsub':
    from gcpdiag.queries import pubsub_stub
    return pubsub_stub.PubsubApiStub()
  elif service_name == 'appengine':
    from gcpdiag.queries import gaes_stub
    return gaes_stub.AppEngineStandardApiStub()
  else:
    raise ValueError('unsupported service: %s' % service_name)
