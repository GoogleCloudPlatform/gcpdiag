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
"""Stub API calls used in gcf.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import json
import re

from gcpdiag.queries import apis_stub

#pylint: disable=unused-argument


class CloudFunctionsApiStub:
  """Mock object to simulate function api calls."""

  def projects(self):
    return self

  def locations(self):
    return self

  def functions(self):
    return self

  def list(self, parent):
    m = re.match(r'projects/([^/]+)/', parent)
    project_id = m.group(1)
    self.json_dir = apis_stub.get_json_dir(project_id)
    return self

  def execute(self, num_retries=0):
    with open(self.json_dir / 'cloudfunctions.json') as json_file:
      return json.load(json_file)
