# Lint as: python3
"""Build and cache GCP APIs + handle authentication."""

import functools
import json
import logging
import os
import pkgutil
import sys
from typing import Dict

import googleapiclient.http
import httplib2
from google.auth import exceptions
from google.auth.transport import requests
from google_auth_oauthlib import flow
from googleapiclient import discovery

from gcp_doctor import cache

_credentials = None


def _get_credentials():
  global _credentials

  # If we have no credentials in memory, fetch from the disk cache.
  if not _credentials:
    with cache.get_cache() as diskcache:
      _credentials = diskcache.get('credentials')

  # Try to refresh the credentials.
  if _credentials and _credentials.expired and _credentials.refresh_token:
    try:
      logging.debug('refreshing credentials')
      _credentials.refresh(requests.Request())
      # Store the refreshed credentials.
      with cache.get_cache() as diskcache:
        diskcache.set('credentials', _credentials)
    except exceptions.RefreshError as e:
      logging.debug("couldn't refresh token: %s", e)

  # Login using browser and verification code.
  if not _credentials or not _credentials.valid:
    logging.debug('No valid credentials found. Initiating auth flow.')
    client_config = json.loads(
        pkgutil.get_data('gcp_doctor.queries', 'client_secrets.json'))
    oauth_flow = flow.Flow.from_client_config(
        client_config,
        scopes=[
            'openid',
            'https://www.googleapis.com/auth/cloud-platform',
            'https://www.googleapis.com/auth/accounts.reauth',
            'https://www.googleapis.com/auth/userinfo.email',
        ],
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
    with cache.get_cache() as diskcache:
      diskcache.set('credentials', _credentials)

  return _credentials


def _request_builder(http, *args, **kwargs):
  if os.getenv('GOOGLE_AUTH_TOKEN'):
    headers = kwargs.get('headers', {})
    headers['x-goog-iam-authorization-token'] = os.getenv('GOOGLE_AUTH_TOKEN')
  return googleapiclient.http.HttpRequest(http, *args, **kwargs)


def login():
  """Force GCP login (this otherwise happens on the first get_api call)."""
  _get_credentials()
  if os.getenv('GOOGLE_AUTH_TOKEN'):
    logging.warning(
        'Using IAM authorization token from GOOGLE_AUTH_TOKEN env. variable.')


def get_user_email() -> str:
  credentials = _get_credentials()
  http = httplib2.Http()
  headers: Dict[str, str] = {}
  credentials.apply(headers)
  resp, content = http.request('https://www.googleapis.com/userinfo/v2/me',
                               'GET',
                               headers=headers)
  if resp['status'] != '200':
    raise RuntimeError(f"can't determine user email. status={resp['status']}")
  data = json.loads(content)
  return data['email']


@functools.lru_cache(maxsize=None)
def get_api(service_name: str, version: str):
  credentials = _get_credentials()
  api = discovery.build(service_name,
                        version,
                        cache_discovery=False,
                        credentials=credentials,
                        requestBuilder=_request_builder)
  return api
