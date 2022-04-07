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
"""Stub API calls used in pubsub.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_PROJECT_NAME = 'gcpdiag-pubsub1-aaaa'


class PubsubApiStub:
  """Mock object to simulate pubsub api calls."""

  def __init__(self, mock_state='init'):
    self.mock_state = mock_state

  def projects(self):
    return self

  def topics(self):
    self.mock_state = 'topics'
    return self

  def subscriptions(self):
    self.mock_state = 'subscription'
    return self

  def list(self, project):
    m = re.match(r'projects/([^/]+)', project)
    project_id = m.group(1)
    if self.mock_state == 'topics':
      return apis_stub.RestCallStub(project_id, 'topics.json')
    if self.mock_state == 'subscription':
      return apis_stub.RestCallStub(project_id, 'subscriptions.json')
    else:
      raise ValueError('incorrect value received')

  def getIamPolicy(self, resource):
    if self.mock_state == 'topics':
      return apis_stub.RestCallStub(DUMMY_PROJECT_NAME, 'topic-iam.json')
    if self.mock_state == 'subscription':
      return apis_stub.RestCallStub(DUMMY_PROJECT_NAME,
                                    'subscriptions-iam.json')
    else:
      raise ValueError('incorrect value received')
