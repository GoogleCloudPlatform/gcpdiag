# Copyright 2022 Google LLC
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
"""Stub API calls used in connectivity.py for testing.

Instead of doing real API calls, we return test JSON data.
"""
import re

from gcpdiag.queries.apis_stub import RestCallStub

# pylint: disable=unused-argument
# pylint: disable=invalid-name


class ConnectivityTestApiStub:
  """Mock object to simulate networkmanagment service api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def global_(self):
    return self

  def connectivityTests(self):
    return self

  def create(self, parent, testId, body):
    m = re.match(r'projects/(.*)/locations/global', parent)
    if m:
      project_id = m.group(1)
      return RestCallStub(project_id, f'operation-{testId}', default={})
    return {}

  def operations(self):
    return self

  def get(self, name):
    m = re.match(r'projects/(.*)/locations/global/operations/(.*)', name)
    if m:
      project_id = m.group(1)
      operation_id = m.group(2)
      return RestCallStub(project_id, operation_id, default={})
    return {}

  def delete(self, name):
    return ConnectivityTestDeleteStub()


class ConnectivityTestDeleteStub:

  def execute(self, num_retries):
    return []
