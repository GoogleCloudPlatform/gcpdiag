# Copyright 2026 Google LLC
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
"""Stub API calls used in managedkafka.py for testing."""

import json
import re
from typing import Optional

import googleapiclient.errors
import httplib2

from gcpdiag.queries import apis_stub


class ManagedKafkaApiStub(apis_stub.ApiStub):
  """Mock object to simulate Managed Kafka API calls."""

  def __init__(self, mock_state: str = 'init', project_id: Optional[str] = None):
    self.mock_state = mock_state
    self.project_id = project_id
    self.resource_path = ''

  def projects(self):
    return self

  def locations(self):
    return self

  def clusters(self):
    self.mock_state = 'clusters'
    return self

  def topics(self):
    if self.mock_state == 'clusters_get' or self.mock_state == 'cluster_get':
      self.mock_state = 'topics'
    else:
      self.mock_state = 'topics'
    return self

  def consumerGroups(self):
    self.mock_state = 'consumerGroups'
    return self

  def acls(self):
    self.mock_state = 'acls'
    return self

  def list(self, name: Optional[str] = None, parent: Optional[str] = None):
    target_path = name or parent or ''
    m = re.match(r'projects/([^/]+)', target_path)
    project_id = m.group(1) if m else 'default'

    if self.mock_state == 'clusters':
      return apis_stub.RestCallStub(project_id, 'clusters')
    elif self.mock_state == 'topics':
      return apis_stub.RestCallStub(project_id, 'topics')
    elif self.mock_state == 'consumerGroups':
      return apis_stub.RestCallStub(project_id, 'consumer-groups')
    elif self.mock_state == 'acls':
      return apis_stub.RestCallStub(project_id, 'acls')
    else:
      return apis_stub.RestCallStub(project_id, 'locations')

  def get(self, name: str, view: Optional[str] = None):
    self.resource_path = name
    if '/topics/' in name:
      self.mock_state = 'topic_get'
    elif '/consumerGroups/' in name:
      self.mock_state = 'consumer_group_get'
    elif '/acls/' in name:
      self.mock_state = 'acl_get'
    else:
      self.mock_state = 'cluster_get'
    return self

  def list_next(self, previous_request, previous_response=None):
    return None

  def execute(self, num_retries: int = 0):
    if self.mock_state == 'cluster_get':
      m = re.match(r'projects/([^/]+)/locations/([^/]+)/clusters/([^/]+)', self.resource_path)
      project_id = m.group(1) if m else 'default'
      json_dir = apis_stub.get_json_dir(project_id)
      with open(json_dir / 'clusters.json', encoding='utf-8') as json_file:
        data = json.load(json_file)
      for c in data.get('clusters', []):
        if c.get('name') == self.resource_path:
          return c
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}), b'not found')

    elif self.mock_state == 'topic_get':
      m = re.match(r'projects/([^/]+)', self.resource_path)
      project_id = m.group(1) if m else 'default'
      json_dir = apis_stub.get_json_dir(project_id)
      with open(json_dir / 'topics.json', encoding='utf-8') as json_file:
        data = json.load(json_file)
      for t in data.get('topics', []):
        if t.get('name') == self.resource_path:
          return t
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}), b'not found')

    elif self.mock_state == 'consumer_group_get':
      m = re.match(r'projects/([^/]+)', self.resource_path)
      project_id = m.group(1) if m else 'default'
      json_dir = apis_stub.get_json_dir(project_id)
      with open(json_dir / 'consumer-groups.json', encoding='utf-8') as json_file:
        data = json.load(json_file)
      for g in data.get('consumerGroups', []):
        if g.get('name') == self.resource_path:
          return g
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}), b'not found')

    elif self.mock_state == 'acl_get':
      m = re.match(r'projects/([^/]+)', self.resource_path)
      project_id = m.group(1) if m else 'default'
      json_dir = apis_stub.get_json_dir(project_id)
      with open(json_dir / 'acls.json', encoding='utf-8') as json_file:
        data = json.load(json_file)
      for a in data.get('acls', []):
        if a.get('name') == self.resource_path:
          return a
      raise googleapiclient.errors.HttpError(httplib2.Response({'status': 404}), b'not found')

    return None
