# Lint as: python3
"""Build and cache GCP APIs"""

import functools
import os
import sys

import googleapiclient.http
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from importlib_resources import files

from gcp_doctor import cache

_credentials = None


def _get_credentials():
  global _credentials

  # Get credentials from the disk cache.
  if not _credentials:
    with cache.get_cache() as diskcache:
      _credentials = diskcache.get('credentials')

  # If we don't have credentials, trigger auth flow.
  if not _credentials or _credentials.expired:
    client_secrets = files('gcp_doctor.queries').joinpath('client_secrets.json')
    flow = Flow.from_client_secrets_file(
        client_secrets,
        scopes=['https://www.googleapis.com/auth/cloud-platform'],
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    auth_url, _ = flow.authorization_url(prompt='consent')
    print('Go to the following link in your browser:\n', file=sys.stderr)
    print('  ' + auth_url, file=sys.stderr)
    print('\nEnter verification code: ', file=sys.stderr, end='')
    code = input()
    print(file=sys.stderr)
    flow.fetch_token(code=code)
    _credentials = flow.credentials

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


@functools.lru_cache(maxsize=None)
def get_api(service_name: str, version: str):
  credentials = _get_credentials()
  api = build(service_name,
              version,
              cache_discovery=False,
              credentials=credentials,
              requestBuilder=_request_builder)
  return api
