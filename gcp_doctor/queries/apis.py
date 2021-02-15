# Lint as: python3
"""Build and cache GCP APIs"""

import functools
import logging
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

  # Try the credentials in memory (_credentials)
  if _credentials and not _credentials.expired:
    return _credentials

  # Try the credentials from the disk cache.
  if not _credentials:
    with cache.get_cache() as diskcache:
      _credentials = diskcache.get('credentials')
      if _credentials and not _credentials.expired:
        logging.debug('Using credentials from diskcache.')
        return _credentials

  # Try application default credentials.
  #
  # Note: this is disabled for now because:
  # - it gives an annoying warning: "No project ID could be determined."
  # - we can't detect properly whether the credentials have expired (!)
  #
  #try:
  #  _credentials, _ = google.auth.default()
  #  logging.debug('Using application-default credentials.')
  #  return _credentials
  #except google.auth.DefaultCredentialsError:
  #  pass

  # Start the auth flow otherwise.
  if not _credentials or _credentials.expired:
    logging.debug('No valid credentials found. Initiating auth flow.')
    client_secrets = files('gcp_doctor.queries').joinpath('client_secrets.json')
    flow = Flow.from_client_secrets_file(
        client_secrets,
        scopes=['https://www.googleapis.com/auth/cloud-platform'],
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    auth_url, _ = flow.authorization_url(prompt='consent')
    print('Go to the following URL in your browser to authenticate:\n',
          file=sys.stderr)
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
  if os.getenv('GOOGLE_AUTH_TOKEN'):
    logging.warning(
        'Using IAM authorization token from GOOGLE_AUTH_TOKEN env. variable.')


@functools.lru_cache(maxsize=None)
def get_api(service_name: str, version: str):
  credentials = _get_credentials()
  api = build(service_name,
              version,
              cache_discovery=False,
              credentials=credentials,
              requestBuilder=_request_builder)
  return api
