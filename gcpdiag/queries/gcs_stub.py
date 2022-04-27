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

from typing import Optional

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

NO_PROJECT_ID_ERROR = 'Not able to call {} without setting project_id for API.'


class BucketApiStub:
  """Mock object to simulate storage api calls.

  Attributes:
    project_id: Since buckets are not explicitly assigned to projects we need a
      project_id to be provided by user to know where to find json_directory
      with bucket data. Without providing it you can still list buckets per
      project.
  """

  def __init__(self, project_id: Optional[str] = None):
    self.project_id = project_id

  def buckets(self):
    return self

  def list(self, project):
    return apis_stub.RestCallStub(project, 'storage')

  def getIamPolicy(self, bucket):
    if not self.project_id:
      raise ValueError(NO_PROJECT_ID_ERROR.format('getIamPolicy'))
    return apis_stub.RestCallStub(self.project_id, 'bucket-roles')
