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

from gcpdiag import caching, config, utils

_credentials = None

AUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/userinfo.email',
]


def _get_credentials():
  global _credentials

  # Authenticate using Application Default Credentials?
  if config.AUTH_ADC:
    logging.debug('auth: using application default credentials')
    if not _credentials:
      _credentials, _ = google.auth.default(scopes=AUTH_SCOPES)
    return _credentials

  # Authenticate using service account key?
  if config.AUTH_KEY:
    logging.debug('auth: using service account key')
    if not _credentials:
      _credentials, _ = google.auth.load_credentials_from_file(
          filename=config.AUTH_KEY, scopes=AUTH_SCOPES)
    return _credentials

  # Oauth: if we have no credentials in memory, fetch from the disk cache.
  if not _credentials:
    with caching.get_cache() as diskcache:
      _credentials = diskcache.get('credentials')

  # Oauth: try to refresh the credentials.
  if _credentials and _credentials.expired and _credentials.refresh_token:
    try:
      logging.debug('refreshing credentials')
      _credentials.refresh(requests.Request())
      # Store the refreshed credentials.
      with caching.get_cache() as diskcache:
        diskcache.set('credentials', _credentials)
    except exceptions.RefreshError as e:
      logging.debug("couldn't refresh token: %s", e)

  # Oauth: login using browser and verification code.
  if not _credentials or not _credentials.valid:
    logging.debug('No valid credentials found. Initiating auth flow.')
    client_config = json.loads(
        pkgutil.get_data('gcpdiag.queries', 'client_secrets.json'))
    oauth_flow = flow.Flow.from_client_config(
        client_config,
        scopes=AUTH_SCOPES +
        ['https://www.googleapis.com/auth/accounts.reauth'],
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    auth_url, _ = oauth_flow.authorization_url(prompt='consent')
    print('Go to the following URL in your browser to authenticate:\n',
          file=sys.stderr)
    print('  ' + auth_url, file=sys.stderr)
    print('\nEnter verification code: ', file=sys.stderr, end='')
    code = input()
    print(file=sys.stderr)
    oauth_flow.fetch_token(code=code)
    _credentials = oauth_flow.credentials

    # Store the credentials in the disk cache.
    with caching.get_cache() as diskcache:
      diskcache.set('credentials', _credentials)

  return _credentials


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

    try:
      # This is for Google-internal use only and allows us to modify the request
      # to make it work also internally. The import will fail for the public
      # version of gcp-doctor.
      # pylint: disable=import-outside-toplevel
      from gcpdiag_google_internal import hooks
      hooks.request_builder_hook(*args, **kwargs)
    except ImportError:
      pass

    if 'headers' in kwargs:
      headers = kwargs.get('headers', {})
      headers['user-agent'] = f'gcp-doctor/{config.VERSION} (gzip)'
      if project_id:
        headers['x-goog-user-project'] = project_id

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
def list_apis(project_id: str) -> Set[str]:
  logging.info('listing enabled APIs')
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
  return f'{service_name}.googleapis.com' in list_apis(project_id)


def verify_access(project_id: str):
  """Verify that the user has access to the project, exit with an error otherwise."""

  try:
    if not is_enabled(project_id, 'cloudresourcemanager'):
      print(
          f'ERROR: Cloud Resource Manager API is required but not enabled in project {project_id}.',
          file=sys.stdout)
      sys.exit(1)
  except utils.GcpApiError as err:
    print(f'ERROR: can\'t access project {project_id}: {err.message}.',
          file=sys.stdout)
    sys.exit(1)
