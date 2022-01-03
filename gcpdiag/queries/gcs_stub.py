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
"""Stub API calls used in gcs.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_PROJECT_NAME = 'gcpdiag-gcs1-aaaa'


class BucketApiStub:
  """Mock object to simulate storage api calls."""

  def __init__(self, mock_state='init', project_id=None, json_dir=None):
    self.mock_state = mock_state
    self.project_id = project_id
    self.json_dir = json_dir

  def buckets(self):
    return self

  def list(self, project):
    json_dir = apis_stub.get_json_dir(project)
    return BucketApiStub('list', project_id=project, json_dir=json_dir)

  def getIamPolicy(self, bucket):
    json_dir = apis_stub.get_json_dir(DUMMY_PROJECT_NAME)
    return BucketApiStub('get_iam_policy',
                         project_id=DUMMY_PROJECT_NAME,
                         json_dir=json_dir)

  def execute(self, num_retries=0):
    del num_retries
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_iam_policy':
      with open(json_dir / 'bucket-roles.json', encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'list':
      with open(self.json_dir / 'storage.json', encoding='utf-8') as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")
