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

# Lint as: python3
"""Build and cache GCP APIs + handle authentication."""

import json
import logging
import os
from typing import Dict, Optional, Set

import google.auth
import google_auth_httplib2
import googleapiclient.http
import httplib2
from google.api_core.client_options import ClientOptions
from google.auth import exceptions
from google.oauth2 import credentials as oauth2_credentials
from googleapiclient import discovery

from gcpdiag import caching, config, hooks, utils

_credentials = None

AUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/userinfo.email',
]


def _auth_method():
  """Calculate proper authentication method based on provided configuration

  Returns:
      str: Return type of authentication method
  """
  if config.get('auth_key'):
    auth_method = 'key'
  elif config.get('auth_adc'):
    auth_method = 'adc'
  else:
    # use ADC by default
    auth_method = 'adc'
  return auth_method


def _get_credentials_adc():
  logging.debug('auth: using application default credentials')

  global _credentials
  if not _credentials:
    # workaround to avoid log message:
    # "WARNING:google.auth._default:No project ID could be determined."
    os.environ.setdefault('GOOGLE_CLOUD_PROJECT', '...fake project id...')
    _credentials, _ = google.auth.default(scopes=AUTH_SCOPES)
  return _credentials


def _get_credentials_key():
  filename = config.get('auth_key')
  logging.debug('auth: using service account key %s', filename)

  global _credentials
  if not _credentials:
    _credentials, _ = google.auth.load_credentials_from_file(filename=filename,
                                                             scopes=AUTH_SCOPES)
  return _credentials


def set_credentials(cred_json):
  global _credentials
  if not cred_json:
    _credentials = None
  else:
    _credentials = oauth2_credentials.Credentials.from_authorized_user_info(
        json.loads(cred_json))


def get_credentials():
  if _auth_method() == 'adc':
    return _get_credentials_adc()
  elif _auth_method() == 'key':
    return _get_credentials_key()
  else:
    raise AssertionError(
        'BUG: AUTH_METHOD method should be one of `adc` or `key`, '
        f'but got `{_auth_method()}` instead.'
        ' Please report at https://gcpdiag.dev/issues/')


def _get_project_or_billing_id(project_id: str) -> str:
  """Return project or billing project id (if defined)"""
  if config.get('billing_project'):
    return config.get('billing_project')
  return project_id


def login():
  """Force GCP login (this otherwise happens on the first get_api call)."""
  get_credentials()


def get_user_email() -> str:
  if config.get('universe_domain') != 'googleapis.com':
    return 'TPC user'
  credentials = get_credentials().with_quota_project(None)

  http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http())
  resp, content = http.request('https://www.googleapis.com/userinfo/v2/me')
  if resp['status'] != '200':
    raise RuntimeError(f"can't determine user email. status={resp['status']}")
  data = json.loads(content)
  logging.debug('determined my email address: %s', data['email'])
  return data['email']


@caching.cached_api_call(in_memory=True)
def get_api(service_name: str,
            version: str,
            project_id: Optional[str] = None,
            region: Optional[str] = None):
  """Get an API object, as returned by googleapiclient.discovery.build.

  If project_id is specified, this will be used as the billed project, and usually
  you should put there the project id of the project that you are inspecting."""
  credentials = get_credentials()

  def _request_builder(http, *args, **kwargs):
    del http

    if 'headers' in kwargs:
      # thread safety: make sure that original dictionary isn't modified
      kwargs['headers'] = kwargs['headers'].copy()

      headers = kwargs.get('headers', {})
      headers['user-agent'] = f'gcpdiag/{config.VERSION} (gzip)'
      if project_id:
        headers['x-goog-user-project'] = _get_project_or_billing_id(project_id)

    hooks.request_builder_hook(*args, **kwargs)

    # thread safety: create a new AuthorizedHttp object for every request
    # https://github.com/googleapis/google-api-python-client/blob/master/docs/thread_safety.md
    new_http = google_auth_httplib2.AuthorizedHttp(credentials,
                                                   http=httplib2.Http())
    return googleapiclient.http.HttpRequest(new_http, *args, **kwargs)

  universe_domain = config.get('universe_domain')
  cred_universe = getattr(credentials, 'universe_domain', 'googleapis.com')
  if cred_universe != universe_domain:
    raise ValueError('credential universe_domain mismatch '
                     f'{cred_universe} != {universe_domain}')
  client_options = ClientOptions()
  if universe_domain != 'googleapis.com':
    client_options.universe_domain = universe_domain
  if region:
    client_options.api_endpoint = f'https://{region}-{service_name}.{universe_domain}'
  else:
    client_options.api_endpoint = f'https://{service_name}.{universe_domain}'
  if service_name in ['compute', 'bigquery', 'storage', 'dns']:
    client_options.api_endpoint += f'/{service_name}/{version}'
  api = discovery.build(service_name,
                        version,
                        cache_discovery=False,
                        credentials=credentials,
                        requestBuilder=_request_builder,
                        client_options=client_options)
  return api


@caching.cached_api_call(in_memory=True)
def _list_enabled_apis(project_id: str) -> Set[str]:
  """List all enabled services available to the specified project"""
  logging.debug('listing enabled APIs')
  serviceusage = get_api('serviceusage', 'v1', project_id)
  request = serviceusage.services().list(parent=f'projects/{project_id}',
                                         filter='state:ENABLED')
  enabled_apis: Set[str] = set()
  try:
    while request is not None:
      response = request.execute(num_retries=config.API_RETRIES)
      if not response:
        logging.debug("No 'services' found in the response for project: %s",
                      project_id)
        break
      services = response.get('services', [])
      if services is None:
        logging.debug("No 'services' found in the response for project: %s",
                      project_id)
        break
      for service in services:
        if 'config' in service and 'name' in service['config']:
          enabled_apis.add(service['config']['name'])
      request = serviceusage.services().list_next(request, response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return enabled_apis


def is_enabled(project_id: str, service_name: str) -> bool:
  universe_domain = config.get('universe_domain')
  return f'{service_name}.{universe_domain}' in _list_enabled_apis(project_id)


def is_all_enabled(project_id: str, services: list) -> Dict[str, str]:
  service_state = {}
  for service in services:
    if not is_enabled(project_id, service):
      service_state[service] = 'DISABLED'
    else:
      service_state[service] = 'ENABLED'
  return service_state


@caching.cached_api_call(in_memory=True)
def list_services_with_state(project_id: str) -> Dict[str, str]:
  logging.debug('listing all APIs with their state')
  serviceusage = get_api('serviceusage', 'v1', project_id)
  request = serviceusage.services().list(parent=f'projects/{project_id}')
  apis_state: Dict[str, str] = {}
  try:
    while request is not None:
      response = request.execute(num_retries=config.API_RETRIES)
      for service in response['services']:
        apis_state.setdefault(service['config']['name'], service['state'])
      request = serviceusage.services().list_next(request, response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return apis_state


def verify_access(project_id: str):
  """Verify that the user has access to the project, exit with an error otherwise."""

  try:
    if not is_enabled(project_id, 'cloudresourcemanager'):
      service = f"cloudresourcemanager.{config.get('universe_domain')}"
      error_msg = (
          'Cloud Resource Manager API must be enabled. To enable, execute:\n'
          f'gcloud services enable {service} --project={project_id}')
      raise utils.GcpApiError(response=error_msg,
                              service=service,
                              reason='SERVICE_DISABLED')
    if not is_enabled(project_id, 'iam'):
      service = f"iam.{config.get('universe_domain')}"
      error_msg = (
          'Identity and Access Management (IAM) API must be enabled. To enable, execute:\n'
          f"gcloud services enable iam.{config.get('universe_domain')} --project={project_id}"
      )
      raise utils.GcpApiError(response=error_msg,
                              service=service,
                              reason='SERVICE_DISABLED')
    if not is_enabled(project_id, 'logging'):
      service = f"logging.{config.get('universe_domain')}"
      warning_msg = (
          'Cloud Logging API is not enabled (related rules will be skipped).'
          ' To enable, execute:\n'
          f"gcloud services enable logging.{config.get('universe_domain')} --project={project_id}\n"
      )
      raise utils.GcpApiError(response=warning_msg,
                              service=service,
                              reason='SERVICE_DISABLED')
  except utils.GcpApiError as err:
    if 'SERVICE_DISABLED' == err.reason:
      if f"serviceusage.{config.get('universe_domain')}" == err.service:
        err.response += (
            '\nService Usage API must be enabled. To enable, execute:\n'
            f"gcloud services enable serviceusage.{config.get('universe_domain')} "
            f'--project={project_id}')
    else:
      logging.error('can\'t access project %s: %s', project_id, err.message)
    raise err
  except exceptions.GoogleAuthError as err:
    logging.error(err)
    if _auth_method() == 'adc':
      logging.error('Error using application default credentials. '
                    'Try running: gcloud auth login --update-adc')
    raise err
  # Plug-in additional authorization verifications
  hooks.verify_access_hook(project_id)
