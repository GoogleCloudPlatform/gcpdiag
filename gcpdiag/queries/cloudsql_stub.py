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
"""Stub API calls used in cloudsql.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


class CloudSQLApiStub:
  """Mock object to simulate CloudSQL api calls."""

  def instances(self):
    return self

  # pylint: disable=invalid-name
  def list(self, project):
    return apis_stub.RestCallStub(project, 'cloudsql-instances', default={})
