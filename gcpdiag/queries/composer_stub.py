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
"""Stub API calls used in composer.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re
from typing import Tuple

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


class ListEnvironmentsQuery:
  """
    Test double for HTTP request for
      https://composer.googleapis.com/v1/projects/{project}/locations/{region}/environments
    API call
  """
  project_id: str
  region: str

  def __init__(self, parent):
    self.project_id, self.region = self.parse_parent(parent)

  def execute(self, num_retries: int = 0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    try:
      with open(json_dir / f'composer-environments-{self.region}.json',
                encoding='utf-8') as f:
        return json.load(f)
    except FileNotFoundError:
      return {}

  def parse_parent(self, parent) -> Tuple[str, str]:
    match = re.match(r'projects/([^/]*)/locations/([^/]*)', parent)
    if not match:
      raise RuntimeError(f"Can't parse parent {parent}")
    return match.group(1), match.group(2)


class ComposerApiStub:
  """Mock object to simulate Composer api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def environments(self):
    return self

  # pylint: disable=invalid-name
  def list(self, parent):
    return ListEnvironmentsQuery(parent)
