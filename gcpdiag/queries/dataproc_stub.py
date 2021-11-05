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
"""Stub API calls used in dataproc.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


class ListClustersQuery:
  """
    Test double for HTTP request for
      https://dataproc.googleapis.com/v1/projects/{project}/regions/{region}/clusters
    API call
  """

  def __init__(self, project_id, region):
    self.project_id = project_id
    self.region = region

  def execute(self, num_retries: int = 0):
    json_dir = apis_stub.get_json_dir(self.project_id)
    try:
      with open(json_dir / f'dataproc-clusters-{self.region}.json',
                encoding='utf-8') as f:
        return json.load(f)
    except FileNotFoundError:
      return {}


class DataprocApiStub:
  """Mock object to simulate dataproc api calls."""

  def projects(self):
    return self

  def regions(self):
    return self

  def clusters(self):
    return self

  # pylint: disable=invalid-name
  def list(self, projectId, region):
    return ListClustersQuery(project_id=projectId, region=region)
