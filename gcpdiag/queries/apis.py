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
import pkgutil
import sys
from typing import Optional, Set

import google.auth
import google_auth_httplib2
import googleapiclient.http
import httplib2
from google.auth import exceptions
from google.auth.transport import requests
from google_auth_oauthlib import flow
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
  elif config.get('auth_oauth'):
    auth_method = 'oauth'
  else:
    # use OAuth by default, except in Cloud Shell
    if config.get('is_cloud_shell'):
      auth_method = 'adc'
    else:
      auth_method = 'oauth'
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


def _oauth_flow_prompt(client_config):
  oauth_flow = flow.Flow.from_client_config(
      client_config,
      scopes=AUTH_SCOPES + ['https://www.googleapis.com/auth/accounts.reauth'],
      redirect_uri='urn:ietf:wg:oauth:2.0:oob')
  while True:
    auth_url, _ = oauth_flow.authorization_url(prompt='consent')
    print('Go to the following URL in your browser to authenticate:\n',
          file=sys.stderr)
    print('  ' + auth_url, file=sys.stderr)
    print('\nEnter verification code: ', file=sys.stderr, end='')
    code = input()
    print(file=sys.stderr)

    os.environ.setdefault('OAUTHLIB_RELAX_TOKEN_SCOPE', 'True')
    token = oauth_flow.fetch_token(code=code)
    if 'https://www.googleapis.com/auth/cloud-platform' in token['scope']:
      return oauth_flow.credentials
    print((
        'ERROR: Cloud Platform scope must be granted. Make sure that you tick all boxes\n'
        '       in the consent screen.\n'),
          file=sys.stderr)


def _get_credentials_oauth():
  logging.debug('auth: using oauth authentication')

  # If we have no credentials in memory, fetch from the disk cache.
  global _credentials
  if not _credentials:
    with caching.get_cache() as diskcache:
      _credentials = diskcache.get('credentials')

  # Try to refresh the credentials.
  if _credentials and _credentials.expired and _credentials.refresh_token:
    try:
      logging.debug('refreshing credentials')
      _credentials.refresh(requests.Request())
      # Store the refreshed credentials.
      with caching.get_cache() as diskcache:
        diskcache.set('credentials', _credentials)
    except exceptions.RefreshError as e:
      logging.debug("couldn't refresh token: %s", e)

  # Login using browser and verification code.
  if not _credentials or not _credentials.valid:
    # Read client id from json file, or fallback to adc if not found.
    try:
      client_config = json.loads(
          pkgutil.get_data('gcpdiag.queries', 'client_secrets.json'))
    except FileNotFoundError:
      logging.warning(
          'client_secrets.json file not found. Using ADC for authentication.')
      return _get_credentials_adc()

    logging.debug('No valid credentials found. Initiating auth flow.')
    _credentials = _oauth_flow_prompt(client_config)

    # Store the credentials in the disk cache.
    with caching.get_cache() as diskcache:
      diskcache.set('credentials', _credentials)

  return _credentials


def _get_credentials():
  if _auth_method() == 'adc':
    return _get_credentials_adc()
  elif _auth_method() == 'key':
    return _get_credentials_key()
  elif _auth_method() == 'oauth':
    return _get_credentials_oauth()
  else:
    raise AssertionError(
        'BUG: AUTH_METHOD method should be one of `adc`, `oauth`, `key`, but got '
        f'`{_auth_method()}` instead.'
        ' Please report at https://gcpdiag.dev/issues/')


def _get_project_or_billing_id(project_id: str) -> str:
  """Return project or billing project id (if defined)"""
  if config.get('billing_project'):
    return config.get('billing_project')
  return project_id


def login():
  """Force GCP login (this otherwise happens on the first get_api call)."""
  _get_credentials()


def get_user_email() -> str:
  credentials = _get_credentials()
  http = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http())
  resp, content = http.request('https://www.googleapis.com/userinfo/v2/me')
  if resp['status'] != '200':
    raise RuntimeError(f"can't determine user email. status={resp['status']}")
  data = json.loads(content)
  logging.debug('determined my email address: %s', data['email'])
  return data['email']


@caching.cached_api_call(in_memory=True)
def get_api(service_name: str, version: str, project_id: Optional[str] = None):
  """Get an API object, as returned by googleapiclient.discovery.build.

  If project_id is specified, this will be used as the billed project, and usually
  you should put there the project id of the project that you are inspecting."""
  credentials = _get_credentials()

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

  api = discovery.build(service_name,
                        version,
                        cache_discovery=False,
                        credentials=credentials,
                        requestBuilder=_request_builder)
  return api


@caching.cached_api_call(in_memory=True)
def _list_apis(project_id: str) -> Set[str]:
  logging.debug('listing enabled APIs')
  serviceusage = get_api('serviceusage', 'v1', project_id)
  request = serviceusage.services().list(parent=f'projects/{project_id}',
                                         filter='state:ENABLED')
  enabled_apis: Set[str] = set()
  try:
    while request is not None:
      response = request.execute(num_retries=config.API_RETRIES)
      for service in response['services']:
        enabled_apis.add(service['config']['name'])
      request = serviceusage.services().list_next(request, response)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return enabled_apis


def is_enabled(project_id: str, service_name: str) -> bool:
  return f'{service_name}.googleapis.com' in _list_apis(project_id)


def verify_access(project_id: str):
  """Verify that the user has access to the project, exit with an error otherwise."""

  try:
    if not is_enabled(project_id, 'cloudresourcemanager'):
      print((
          'ERROR: Cloud Resource Manager API must be enabled. To enable, execute:\n'
          f'gcloud services enable cloudresourcemanager.googleapis.com --project={project_id}'
      ),
            file=sys.stdout)
      sys.exit(1)

    if not is_enabled(project_id, 'iam'):
      print((
          'ERROR: Identity and Access Management (IAM) API must be enabled. To enable, execute:\n'
          f'gcloud services enable iam.googleapis.com --project={project_id}'),
            file=sys.stdout)
      sys.exit(1)

    if not is_enabled(project_id, 'logging'):
      print((
          'WARNING: Cloud Logging API is not enabled (related rules will be skipped).'
          ' To enable, execute:\n'
          f'gcloud services enable logging.googleapis.com --project={project_id}\n'
      ),
            file=sys.stdout)
  except utils.GcpApiError as err:
    if 'SERVICE_DISABLED' == err.reason and 'serviceusage.googleapis.com' == err.service:
      print((
          'ERROR: Service Usage API must be enabled. To enable, execute:\n'
          f'gcloud services enable serviceusage.googleapis.com --project={project_id}'
      ),
            file=sys.stdout)
    else:
      print(f'ERROR: can\'t access project {project_id}: {err.message}.',
            file=sys.stdout)
    sys.exit(1)
  except exceptions.GoogleAuthError as err:
    print(f'ERROR: {err}', file=sys.stdout)
    if _auth_method() == 'adc':
      print(('Error using application default credentials. '
             'Try running: gcloud auth login --update-adc'),
            file=sys.stderr)
    sys.exit(1)

  # Plug-in additional authorization verifications
  hooks.verify_access_hook(project_id)
