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

import json
import re

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_PROJECT_NAME = 'gcpdiag-pubsub1-aaaa'


class PubsubApiStub:
  """Mock object to simulate pubsub api calls."""

  def __init__(self, mock_state='init', project_id=None, json_dir=None, p=None):
    self.mock_state = mock_state
    self.project_id = project_id
    self.json_dir = json_dir
    self.p = p

  def projects(self):
    return self

  def topics(self):
    self.p = 'topics'
    return self

  def subscriptions(self):
    self.p = 'subscription'
    return self

  def list(self, project):
    m = re.match(r'projects/([^/]+)', project)
    project_id = m.group(1)
    json_dir = apis_stub.get_json_dir(project_id)
    if self.p == 'topics':
      return PubsubApiStub('list-topic',
                           project_id=DUMMY_PROJECT_NAME,
                           json_dir=json_dir)
    if self.p == 'subscription':
      return PubsubApiStub('list-subscription',
                           project_id=DUMMY_PROJECT_NAME,
                           json_dir=json_dir)
    else:
      raise ValueError('incorrect value received')

  def getIamPolicy(self, resource):
    json_dir = apis_stub.get_json_dir(DUMMY_PROJECT_NAME)
    if self.p == 'topics':
      return PubsubApiStub('get_iam_policy-topic',
                           project_id=DUMMY_PROJECT_NAME,
                           json_dir=json_dir)
    if self.p == 'subscription':
      return PubsubApiStub('get_iam_policy-subscription',
                           project_id=DUMMY_PROJECT_NAME,
                           json_dir=json_dir)
    else:
      raise ValueError('incorrect value received')

  def execute(self, num_retries=0):
    del num_retries
    json_dir = apis_stub.get_json_dir(self.project_id)
    if self.mock_state == 'get_iam_policy-topic':
      with open(json_dir / 'topic-iam.json', encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'get_iam_policy-subscription':
      with open(self.json_dir / 'subscriptions-iam.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'list-topic':
      with open(self.json_dir / 'topics.json', encoding='utf-8') as json_file:
        return json.load(json_file)
    elif self.mock_state == 'list-subscription':
      with open(self.json_dir / 'subscriptions.json',
                encoding='utf-8') as json_file:
        return json.load(json_file)
    else:
      raise ValueError("can't call this method here")
