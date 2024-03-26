# Copyright 2024 Google LLC
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
"""Stub API calls used in requests module for testing.

Instead of doing real API calls, we return test JSON data.
"""
import json
import re

DUMMY_USER_COMPUTE_PROFILE_NAME_SPACE_NAME = 'namespace_test'


def request(*args, **kwargs):
  """Mock object to simulate HTTP response."""

  class MockResponse:

    def __init__(self, json_data, status_code):
      self.json_data = json_data
      self.status_code = status_code

    def json(self):
      return self.json_data

  if 'headers' in kwargs:
    pass
  match_1 = re.match(r'.+/v3/profiles$', args[1])
  match_2 = re.match(r'.+/v3/namespaces$', args[1])
  match_3 = re.match(r'.+/v3/namespaces/[^/]+/profiles$', args[1])
  if args[0] == 'GET' and match_1:
    with open(
        'test-data/datafusion1/json-dumps/datafusion-system-compute-profile.json',
        encoding='utf-8') as json_file:
      json_data = json.load(json_file)
      status_code = 200
    return MockResponse(json_data, status_code)
  elif args[0] == 'GET' and match_2:
    with open('test-data/datafusion1/json-dumps/namespaces.json',
              encoding='utf-8') as json_file:
      json_data = json.load(json_file)
      status_code = 200
    return MockResponse(json_data, status_code)
  elif args[0] == 'GET' and match_3:
    m = re.match(r'.+/v3/namespaces/([^/])+/profiles$', args[1])
    m = m.group(0)
    url = m.split('/')
    if url[-2] == DUMMY_USER_COMPUTE_PROFILE_NAME_SPACE_NAME:
      with open(
          'test-data/datafusion1/json-dumps/datafusion-user-compute-profile.json',
          encoding='utf-8') as json_file:
        json_data = json.load(json_file)
        status_code = 200
      return MockResponse(json_data, status_code)
