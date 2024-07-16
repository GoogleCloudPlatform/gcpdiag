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
# pylint: disable=cyclic-import
"""Stub API calls used in apis.py for testing."""

import json
import pathlib
import re
from typing import Optional

import googleapiclient.errors
import httplib2

# pylint: disable=unused-argument
JSON_PROJECT_DIR = {
    'gcpdiag-apigee1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/apigee1/json-dumps',
    '12340005':
        pathlib.Path(__file__).parents[2] / 'test-data/apigee1/json-dumps',
    'gcpdiag-gce1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    '12340001':
        pathlib.Path(__file__).parents[2] / 'test-data/gce1/json-dumps',
    'gcpdiag-gce-faultyssh-runbook':
        pathlib.Path(__file__).parents[2] / 'test-data/gce2/json-dumps',
    '12345601':
        pathlib.Path(__file__).parents[2] / 'test-data/gce2/json-dumps',
    'gcpdiag-gce-vm-performance':
        pathlib.Path(__file__).parents[2] / 'test-data/gce4/json-dumps',
    '123456270':
        pathlib.Path(__file__).parents[2] / 'test-data/gce4/json-dumps',
    'gcpdiag-bigquery1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/bigquery1/json-dumps',
    'gcpdiag-gke1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
    '12340002':
        pathlib.Path(__file__).parents[2] / 'test-data/gke1/json-dumps',
    'gcpdiag-gcf1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gcf1/json-dumps',
    '12340003':
        pathlib.Path(__file__).parents[2] / 'test-data/gcf1/json-dumps',
    'gcpdiag-gcs1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gcs1/json-dumps',
    'gcpdiag-datafusion1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/datafusion1/json-dumps',
    '12340010':
        pathlib.Path(__file__).parents[2] / 'test-data/datafusion1/json-dumps',
    'gcpdiag-dataproc1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/dataproc1/json-dumps',
    'gcpdiag-composer1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/composer1/json-dumps',
    'gcpdiag-cloudsql1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudsql1/json-dumps',
    'gcpdiag-cloudasset1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudasset1/json-dumps',
    '12340071':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudasset1/json-dumps',
    'gcpdiag-fw-policy-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/fw-policy/json-dumps',
    '12340004':
        pathlib.Path(__file__).parents[2] / 'test-data/fw-policy/json-dumps',
    'gcpdiag-pubsub1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/pubsub1/json-dumps',
    '12340014':
        pathlib.Path(__file__).parents[2] / 'test-data/pubsub1/json-dumps',
    'gcpdiag-gaes1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gaes1/json-dumps',
    'gcpdiag-gcb1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gcb1/json-dumps',
    'gcpdiag-vpc1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/vpc1/json-dumps',
    'gcpdiag-lb1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/lb1/json-dumps',
    'gcpdiag-lb2-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/lb2/json-dumps',
    'gcpdiag-lb3-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/lb3/json-dumps',
    'gcpdiag-tpu1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/tpu1/json-dumps',
    'gcpdiag-iam1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/iam1/json-dumps',
    'gcpdiag-cloudrun1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudrun1/json-dumps',
    '123400010':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudrun1/json-dumps',
    'gcpdiag-cloudrun2-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/cloudrun2/json-dumps',
    'gcpdiag-notebooks1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/notebooks1/json-dumps',
    'gcpdiag-notebooks2-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/notebooks2/json-dumps',
    'gcpdiag-dataflow1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/dataflow1/json-dumps',
    'gcpdiag-vertex1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/vertex1/json-dumps',
    'gcpdiag-billing1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/billing1/json-dumps',
    'gcpdiag-billing2-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/billing1/json-dumps',
    'gcpdiag-billing3-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/billing1/json-dumps',
    'gcpdiag-osconfig1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/osconfig1/json-dumps',
    'gcpdiag-gke-cluster-autoscaler-rrrr':
        pathlib.Path(__file__).parents[2] / 'test-data/gke2/json-dumps',
    '1234000173':
        pathlib.Path(__file__).parents[2] / 'test-data/gke2/json-dumps',
    'gcpdiag-vpc2-runbook':
        pathlib.Path(__file__).parents[2] / 'test-data/vpc2/json-dumps',
    '12345602':
        pathlib.Path(__file__).parents[2] / 'test-data/vpc2/json-dumps',
    'gcpdiag-gce3-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gce3/json-dumps',
    '12345001':
        pathlib.Path(__file__).parents[2] / 'test-data/gce3/json-dumps',
    'gcpdiag-gke3-gggg':
        pathlib.Path(__file__).parents[2] / 'test-data/gke3/json-dumps',
    '12340032':
        pathlib.Path(__file__).parents[2] / 'test-data/gke3/json-dumps',
    'gcpdiag-gke4-runbook':
        pathlib.Path(__file__).parents[2] / 'test-data/gke4/json-dumps',
    'gcpdiag-nat1-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/nat1/json-dumps',
    '12340033':
        pathlib.Path(__file__).parents[2] / 'test-data/gke4/json-dumps',
    'centos-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'cos-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'debian-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'fedora-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'fedora-coreos-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'opensuse-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'rhel-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'rhel-sap-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'rocky-linux-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'suse-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'suse-sap-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'ubuntu-os-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'ubuntu-os-pro-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'windows-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'windows-sql-cloud':
        pathlib.Path(__file__).parents[2] /
        'test-data/gce-image-license/json-dumps',
    'gcpdiag-gce5-aaaa':
        pathlib.Path(__file__).parents[2] / 'test-data/gce5/json-dumps',
    '123456012345':
        pathlib.Path(__file__).parents[2] / 'test-data/gce5/json-dumps',
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


class RestCallStub(ApiStub):
  """Generic mock object to simulate executable api request."""

  def __init__(self,
               project_id: str,
               json_basename: str,
               *,
               page: int = 1,
               default: Optional[dict] = None,
               default_json_basename: Optional[str] = None,
               request_uri: str = ''):
    self.project_id = project_id
    self.json_dir = get_json_dir(project_id)
    self.json_basename = json_basename
    self.page = page
    self.default = default
    self.default_json_basename = default_json_basename
    self.uri = request_uri

  def execute(self, num_retries: int = 0) -> dict:
    self._maybe_raise_api_exception()
    try:
      filename = str(self.json_dir / self.json_basename)
      if self.page > 1:
        filename += f'-{self.page}'
      filename += '.json'
      with open(filename, encoding='utf-8') as json_file:
        return json.load(json_file)
    except FileNotFoundError:
      if self.default is not None:
        return self.default
      if self.default_json_basename is not None:
        with open(str(self.json_dir / self.default_json_basename) + '.json',
                  encoding='utf-8') as json_file:
          return json.load(json_file)
      raise


class ServiceUsageApiStub(ApiStub):
  """Mock object to simulate api calls."""

  def __init__(self, mock_state=None, project_id=None, service=None):
    self._mock_state = mock_state
    self._project_id = project_id
    self._service = service

  def services(self):
    return self

  # pylint: disable=redefined-builtin
  def list(self, parent, filter):
    m = re.match(r'projects/([^/]+)', parent)
    if not m:
      raise ValueError(f"can't parse parent: {parent}")
    project_id = m.group(1)
    return RestCallStub(project_id, 'services')

  def list_next(self, request, response):
    return None

  def get(self, name):
    m = re.match(r'projects/([^/]+)/services/([^/]+)', name)
    if not m:
      raise ValueError(f"can't parse name: {name}")
    return ServiceUsageApiStub(mock_state='get',
                               project_id=m.group(1),
                               service=m.group(2))

  def execute(self, num_retries=0):
    self._maybe_raise_api_exception()
    json_dir = get_json_dir(self._project_id)
    with open(json_dir / 'services.json', encoding='utf-8') as json_file:
      services_list = json.load(json_file)
      if self._mock_state == 'get':
        for service in services_list.get('services', []):
          if service.get('config', {}).get('name') \
              == f'{self._service}':
            return service
        return {'state': 'DISABLED'}


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
                 project_id: Optional[str] = None,
                 regional_service_endpoint: Optional[str] = None):

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

    # project_id isn't required in serviceaccounts.get requests
    # and it cannot be easily extracted from a service account name
    # thus passing api_project_id to determine the correct test-data
    return iam_stub.IamApiStub(project_id)
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
  elif service_name == 'datafusion':
    from gcpdiag.queries import datafusion_stub
    return datafusion_stub.DataFusionApiStub()
  elif service_name == 'dataproc':
    from gcpdiag.queries import dataproc_stub
    return dataproc_stub.DataprocApiStub()
  elif service_name == 'apigee':
    from gcpdiag.queries import apigee_stub
    return apigee_stub.ApigeeApiStub()
  elif service_name == 'composer':
    from gcpdiag.queries import composer_stub
    return composer_stub.ComposerApiStub()
  elif service_name == 'sqladmin':
    from gcpdiag.queries import cloudsql_stub
    return cloudsql_stub.CloudSQLApiStub()
  elif service_name == 'storage':
    from gcpdiag.queries import gcs_stub

    # project_id isn't required in buckets.get and buckets.getIamPolicy requests
    # and it cannot be extracted from bucket name
    # thus passing api_project_id to determine the correct test-data
    return gcs_stub.BucketApiStub(project_id)
  elif service_name == 'cloudbuild':
    from gcpdiag.queries import gcb_stub
    return gcb_stub.CloudBuildApiStub()
  elif service_name == 'pubsub':
    from gcpdiag.queries import pubsub_stub
    return pubsub_stub.PubsubApiStub()
  elif service_name == 'appengine':
    from gcpdiag.queries import gae_stub
    return gae_stub.AppEngineApiStub()
  elif service_name == 'artifactregistry':
    from gcpdiag.queries import artifact_registry_stub
    return artifact_registry_stub.ArtifactRegistryApiStub()
  elif service_name == 'run':
    from gcpdiag.queries import cloudrun_stub
    return cloudrun_stub.CloudRunApiStub()
  elif service_name == 'notebooks':
    from gcpdiag.queries import notebooks_stub
    return notebooks_stub.NotebooksApiStub()
  elif service_name == 'dataflow':
    from gcpdiag.queries import dataflow_stub
    return dataflow_stub.DataflowApiStub()
  elif 'aiplatform' in service_name:
    from gcpdiag.queries import vertex_stub
    return vertex_stub.VertexApiStub()
  elif service_name == 'recommender':
    from gcpdiag.queries import recommender_stub
    return recommender_stub.RecommenderApiStub()
  elif service_name == 'cloudbilling':
    from gcpdiag.queries import billing_stub
    return billing_stub.BillingApiStub()
  elif service_name == 'osconfig':
    from gcpdiag.queries import osconfig_stub
    return osconfig_stub.OSConfigStub()
  elif service_name == 'networkmanagement':
    from gcpdiag.queries import networkmanagement_stub
    return networkmanagement_stub.NetworkManagementApiStub()
  elif service_name == 'cloudasset':
    from gcpdiag.queries import cloudasset_stub
    return cloudasset_stub.CloudAssetApiStub()
  else:
    raise ValueError('unsupported service: %s' % service_name)
