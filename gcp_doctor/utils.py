# Lint as: python3
"""Various utility functions."""

import json
import re

from googleapiclient import errors

from gcp_doctor import config
from gcp_doctor.queries import apis

DOMAIN_RES_NAME_MATCH = r'(http(s)?:)?//([a-z0-9][-a-z0-9]{1,61}[a-z0-9]\.)+[a-z]{2,}/'
RES_NAME_KEY = r'[a-z][-a-z0-9]*'
RES_NAME_VALUE = r'[a-z0-9][-a-z0-9]*'
REL_RES_NAME_MATCH = r'({key}/{value}/)*{key}/{value}'.format(
    key=RES_NAME_KEY, value=RES_NAME_VALUE)
REGION_NAME_MATCH = r'^\w+-\w+$'
FULL_RES_NAME_MATCH = DOMAIN_RES_NAME_MATCH + REL_RES_NAME_MATCH


class GcpApiError(Exception):
  """Exception raised for GCP API/HTTP errors.

  Attributes: response -- API/HTTP response
  """

  def __init__(self, response='An error occured during the GCP API call'):
    self.response = response
    # see also: https://github.com/googleapis/google-api-python-client/issues/662
    try:
      content = json.loads(response.content)
      if isinstance(
          content,
          dict) and 'error' in content and 'message' in content['error']:
        self.message = content['error']['message']
      else:
        self.message = str(response)
    except json.decoder.JSONDecodeError:
      self.message = content
    super().__init__(self.message)

  def __str__(self):
    return f'can\'t fetch data, reason: {self.message}'


def extract_value_from_res_name(resource_name: str, key: str) -> str:
  """Extract a value by a key from a resource name.

  Example:
      resource_name: projects/testproject/zones/us-central1-c
      key: zones
      return value: us-central1-c
  """
  if not is_valid_res_name(resource_name):
    raise ValueError('invalid resource name')

  path_items = resource_name.split('/')
  for i, item in enumerate(path_items):
    if item == key:
      if i + 1 < len(path_items):
        return path_items[i + 1]
      else:
        break
  raise ValueError('invalid resource name')


def get_region_by_res_name(res_name: str) -> str:
  return extract_value_from_res_name(res_name, 'locations')


def get_zone_by_res_name(res_name: str) -> str:
  return extract_value_from_res_name(res_name, 'zones')


def get_project_by_res_name(res_name: str) -> str:
  return extract_value_from_res_name(res_name, 'projects')


def is_region(name: str) -> bool:
  return bool(re.match(REGION_NAME_MATCH, name))


def is_full_res_name(res_name: str) -> bool:
  return bool(re.fullmatch(FULL_RES_NAME_MATCH, res_name, flags=re.IGNORECASE))


def is_rel_res_name(res_name: str) -> bool:
  return bool(re.fullmatch(REL_RES_NAME_MATCH, res_name, flags=re.IGNORECASE))


def is_valid_res_name(res_name: str) -> bool:
  return is_rel_res_name(res_name) or is_full_res_name(res_name)


# see also: https://github.com/googleapis/google-api-python-client/issues/662
def http_error_message(err: errors.HttpError) -> str:
  # TODO: use GcpApiError exception instead of this function
  content = json.loads(err.content)
  if isinstance(content,
                dict) and 'error' in content and 'message' in content['error']:
    return content['error']['message']
  else:
    return str(err)


def report_usage_if_running_at_google(command, details=None):
  """For Google-internal use: report usage statistics."""
  try:
    # Try the import first, because this will fail faster than checking the
    # user (which is we check later that it is in the google.com domain).
    # pylint: disable=import-outside-toplevel
    from gcp_doctor_google_internal import cta_client

    # Only do this for google.com users.
    email = apis.get_user_email()
    match_google = re.match('(.*)@google.com$', email)
    if match_google:
      user = match_google.group(1)
      if not details:
        details = {}
      details['version'] = config.VERSION
      cta_client.submit(user, 'gcp-doctor', command, details)
    print('How good were the results? https://forms.gle/jG1dUdkxhP2s5ced6')
  except RuntimeError:
    pass
