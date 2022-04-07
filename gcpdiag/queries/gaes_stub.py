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
"""Stub API calls used in gaes.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument
#pylint: disable=invalid-name


class AppEngineStandardApiStub(apis_stub.ApiStub):
  """Mock object to simulate App Engine Standard api calls."""

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def apps(self):
    return self

  def services(self):
    return AppEngineStandardApiStub('services')

  def versions(self):
    return AppEngineStandardApiStub('versions')

  def list(self, appsId='appsId', servicesId='servicesId'):
    if self.mock_state == 'services':
      return apis_stub.RestCallStub(appsId, 'appengine_services.json')
    else:
      return apis_stub.RestCallStub(appsId, 'versions.json')
