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
"""Stub API calls used in logs.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

# pylint: disable=unused-argument
# pylint: disable=invalid-name

from gcpdiag import utils
from gcpdiag.queries import apis_stub

GKE1_PROJECT = 'gcpdiag-gke1-aaaa'

logging_body = None


class LoggingApiStub:
  """Mock object to simulate container api calls."""
  body: str

  def entries(self):
    return self

  def list(self, body):
    global logging_body
    logging_body = body
    project = utils.get_project_by_res_name(body['resourceNames'][0])
    return apis_stub.RestCallStub(project, 'logging-entries-1')

  def list_next(self, req, res):
    del req, res
