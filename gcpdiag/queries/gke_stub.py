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
"""Stub API calls used in gke.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

from gcpdiag import utils
from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument


class ContainerApiStub(apis_stub.ApiStub):
  """Mock object to simulate container api calls."""

  def __init__(self, mock_state='init', project_id=None, region=None):
    self.mock_state = mock_state
    self.project_id = project_id
    self.region = region

  def projects(self):
    return self

  def locations(self):
    return self

  def clusters(self):
    return ContainerApiStub(mock_state='clusters')

  # pylint: disable=invalid-name
  def getServerConfig(self, name):
    project_id = utils.get_project_by_res_name(name)
    region = utils.get_region_by_res_name(name)
    return ContainerApiStub(mock_state='server_config',
                            project_id=project_id,
                            region=region)

  def list(self, parent):
    m = re.match(r'projects/([^/]+)/', parent)
    self.project_id = m.group(1)
    return self

  def execute(self, num_retries=0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'clusters':
      with open(json_dir / 'container-clusters.json',
                encoding='utf8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'server_config':
      with open(json_dir / f'container-server-config-{self.region}.json',
                encoding='utf8') as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")
