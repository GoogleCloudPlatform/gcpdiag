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
from typing import Any, Dict, List, Optional

DOMAIN_RES_NAME_MATCH = r'(http(s)?:)?//([a-z0-9][-a-z0-9]{1,61}[a-z0-9]\.)+[a-z]{2,}/'
RES_NAME_KEY = r'[a-z][-a-z0-9]*'
RES_NAME_VALUE = r'[a-z0-9][-a-z0-9_?]*'
REL_RES_NAME_MATCH = r'({key}/{value}/)*{key}/{value}'.format(
    key=RES_NAME_KEY, value=RES_NAME_VALUE)
REGION_NAME_MATCH = r'^\w+-\w+$'
ZONE_NAME_MATCH = r'^(\w+-\w+)-\w+$'
FULL_RES_NAME_MATCH = DOMAIN_RES_NAME_MATCH + REL_RES_NAME_MATCH


class VersionComponentsParser:
  """ Simple helper class to parse version string to components """

  version_str: str

  def __init__(self, version_str: str):
    self.version_str = str(version_str)

  def get_components(self) -> List[int]:
    cs = [int(s) for s in self.extract_base_version().split('.')]
    # example: 1 -> 1.0.0, 1.2 -> 1.2.0
    cs += [0] * (3 - len(cs))
    return cs

  def extract_base_version(self) -> str:
    m = re.search(r'^[\d\.]+', self.version_str)
    if m is None:
      raise Exception(f'Can not parse version {self.version_str}')
    return m.group(0)


class Version:
  """ Represents Version """

  version_str: str
  major: int
  minor: int
  patch: int

  def __init__(self, version_str: str):
    # example: 1.19.13-gke.701
    self.version_str = version_str
    self.major, self.minor, self.patch = \
      VersionComponentsParser(version_str).get_components()

  def same_major(self, other_version: 'Version') -> bool:
    return self.major == other_version.major

  def diff_minor(self, other_version: 'Version') -> int:
    return abs(self.minor - other_version.minor)

  def __str__(self) -> str:
    return self.version_str

  def __add__(self, other: object) -> object:
    if isinstance(other, str):
      return self.version_str + other
    raise TypeError(f'Can not concatenate Version and {type(other)}')

  def __radd__(self, other: object) -> object:
    if isinstance(other, str):
      return other + self.version_str
    raise TypeError(f'Can not concatenate and {type(other)} Version')

  def __eq__(self, other: object) -> bool:
    if isinstance(other, str):
      return other == self.version_str
    if isinstance(other, Version):
      return self.version_str == other.version_str
    raise AttributeError('Can not compare Version object with {}'.format(
        type(other)))

  def __lt__(self, other):
    return self.major < other.major or self.minor < other.minor or self.patch < other.patch

  def __ge__(self, other):
    return self.major >= other.major and self.minor >= other.minor and self.patch >= other.patch


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
    self.reason = None
    self.service = None
    # see also: https://github.com/googleapis/google-api-python-client/issues/662
    try:
      content = json.loads(response.content)
      if isinstance(
          content,
          dict) and 'error' in content and 'message' in content['error']:
        self.message = content['error']['message']
        try:
          for c in content['error']['details']:
            if c['@type'] == 'type.googleapis.com/google.rpc.ErrorInfo':
              self.reason = c['reason']
              self.service = c['metadata']['service']
        except KeyError:
          pass
      else:
        self.message = str(response)
    except json.decoder.JSONDecodeError:
      self.message = response.content
    if isinstance(self.message, bytes):
      self.message = self.message.decode('utf-8')
    super().__init__(self.message)

  def __str__(self):
    return self.message


def extract_value_from_res_name(resource_name: str, key: str) -> str:
  """Extract a value by a key from a resource name.

  Example:
      resource_name: projects/testproject/zones/us-central1-c
      key: zones
      return value: us-central1-c
  """
  if not is_valid_res_name(resource_name):
    raise ValueError(f'invalid resource name: {resource_name}')

  path_items = resource_name.split('/')
  for i, item in enumerate(path_items):
    if item == key:
      if i + 1 < len(path_items):
        return path_items[i + 1]
      else:
        break
  raise ValueError(f'invalid resource name: {resource_name}')


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


def iter_dictlist(dictlist: Dict[Any, List[Any]]):
  """Given a dictionary of lists, iterate over the list elements returning
  tuples (dict_key, item), (dict_key, item), ..."""

  for (k, v) in dictlist.items():
    for i in v:
      yield (k, i)
