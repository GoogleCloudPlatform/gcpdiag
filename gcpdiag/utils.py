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
"""Various utility functions."""

import json
import re
from typing import Optional

DOMAIN_RES_NAME_MATCH = r'(http(s)?:)?//([a-z0-9][-a-z0-9]{1,61}[a-z0-9]\.)+[a-z]{2,}/'
RES_NAME_KEY = r'[a-z][-a-z0-9]*'
RES_NAME_VALUE = r'[a-z0-9][-a-z0-9]*'
REL_RES_NAME_MATCH = r'({key}/{value}/)*{key}/{value}'.format(
    key=RES_NAME_KEY, value=RES_NAME_VALUE)
REGION_NAME_MATCH = r'^\w+-\w+$'
ZONE_NAME_MATCH = r'^(\w+-\w+)-\w+$'
FULL_RES_NAME_MATCH = DOMAIN_RES_NAME_MATCH + REL_RES_NAME_MATCH


class GcpApiError(Exception):
  """Exception raised for GCP API/HTTP errors.

  Attributes: response -- API/HTTP response
  """

  @property
  def status(self) -> Optional[int]:
    try:
      return self.response.resp.status
    except KeyError:
      return None

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
      self.message = response.content
    if isinstance(self.message, bytes):
      self.message = self.message.decode('utf-8')
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


def zone_region(zone: str) -> str:
  """Get region name of a zone."""
  m = re.match(ZONE_NAME_MATCH, zone)
  if not m:
    raise ValueError('can\'t parse zone name: <%s>' % zone)
  return m.group(1)


def is_full_res_name(res_name: str) -> bool:
  return bool(re.fullmatch(FULL_RES_NAME_MATCH, res_name, flags=re.IGNORECASE))


def is_rel_res_name(res_name: str) -> bool:
  return bool(re.fullmatch(REL_RES_NAME_MATCH, res_name, flags=re.IGNORECASE))


def is_valid_res_name(res_name: str) -> bool:
  return is_rel_res_name(res_name) or is_full_res_name(res_name)
