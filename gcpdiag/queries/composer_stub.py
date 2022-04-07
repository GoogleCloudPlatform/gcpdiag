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

import re

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


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
    match = re.match(r'projects/([^/]*)/locations/([^/]*)', parent)
    if not match:
      raise RuntimeError(f"Can't parse parent {parent}")
    project_id, region = match.group(1), match.group(2)
    return apis_stub.RestCallStub(project_id,
                                  f'composer-environments-{region}.json',
                                  default={})
