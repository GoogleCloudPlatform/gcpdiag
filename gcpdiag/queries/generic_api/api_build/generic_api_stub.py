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
"""Stub API calls used in apis.py for testing."""

import json
import os

# pylint: disable=unused-argument


class GenericApiStub:
  """Attributes:

  project_root:
  data_dir:
  """

  def __init__(self, service_name: str):
    self.project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
    self.data_dir = os.path.join(self.project_root, 'test-data', service_name,
                                 'json-dumps')

  def _load_json(self, file_name: str) -> dict:
    file_path = os.path.join(self.data_dir, file_name)
    file_path = str(file_path + '.json')
    if not os.path.exists(file_path):
      raise FileNotFoundError('file not found: %s' % file_path)
    with open(file_path, encoding='utf-8') as file:
      return json.load(file)


def get_generic_api_stub(service_name: str, api_base_url: str):

  # Avoid circular import dependencies by importing the required modules here.
  # pylint: disable=import-outside-toplevel

  if service_name == 'datafusion':
    from gcpdiag.queries.generic_api.datafusion import datafusion_stub
    return datafusion_stub.DataFusionApiStub()
  else:
    raise ValueError('unsupported endpoint: %s' % service_name)
