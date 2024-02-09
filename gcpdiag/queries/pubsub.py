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
"""Queries related to GCP PubSub

"""

import logging
import re
from typing import Dict, Mapping, Union

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, iam


class Topic(models.Resource):
  """Represent a Topic"""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None

  @property
  def name(self) -> str:
    m = re.search(r'/topics/([^/]+)$', self._resource_data['name'])
    if not m:
      raise RuntimeError('can\'t determine name of topic %s' %
                         (self._resource_data['name']))
    return m.group(1)

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def kms_key_name(self) -> str:
    return self._resource_data['kmsKeyName']


@caching.cached_api_call
def get_topics(context: models.Context) -> Mapping[str, Topic]:
  """Get all topics(Does not include deleted topics)."""
  topics: Dict[str, Topic] = {}
  if not apis.is_enabled(context.project_id, 'pubsub'):
    return topics
  pubsub_api = apis.get_api('pubsub', 'v1', context.project_id)
  logging.info('fetching list of PubSub topics in project %s',
               context.project_id)
  query = pubsub_api.projects().topics().list(
      project=f'projects/{context.project_id}')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'topics' not in resp:
      return topics
    for t in resp['topics']:
      # verify that we have some minimal data that we expect
      if 'name' not in t:
        raise RuntimeError('missing data in topics response')
        # projects/{project}/topics/{topic}
      result = re.match(r'projects/[^/]+/topics/([^/]+)', t['name'])
      if not result:
        logging.error('invalid topic data: %s', t['name'])
        continue

      if not context.match_project_resource(resource=result.group(1),
                                            labels=t.get('labels', {})):
        continue

      topics[t['name']] = Topic(project_id=context.project_id, resource_data=t)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return topics


class TopicIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_topic_iam_policy(name: str) -> TopicIAMPolicy:
  project_id = utils.get_project_by_res_name(name)

  pubsub_api = apis.get_api('pubsub', 'v1', project_id)
  request = pubsub_api.projects().topics().getIamPolicy(resource=name)

  return iam.fetch_iam_policy(request, TopicIAMPolicy, project_id, name)


class Subscription(models.Resource):
  """Represent a Subscription."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None

  @property
  def name(self) -> str:
    m = re.search(r'/subscriptions/([^/]+)$', self._resource_data['name'])
    if not m:
      raise RuntimeError('can\'t determine name of subscription %s' %
                         (self._resource_data['name']))
    return m.group(1)

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def topic(self) -> Union[Topic, str]:
    """
    Return subscription's topic as a Topic object,
    or String '_deleted-topic_' if topic is deleted.
    """
    if 'topic' not in self._resource_data:
      raise RuntimeError('topic not set for subscription {self.name}')
    elif self._resource_data['topic'] == '_deleted-topic_':
      return '_deleted_topic_'

    m = re.match(r'projects/([^/]+)/topics/([^/]+)',
                 self._resource_data['topic'])
    if not m:
      raise RuntimeError("can't parse topic: %s" % self._resource_data['topic'])
    (project_id, topic_name) = (m.group(1), self._resource_data['topic'])
    topics = get_topics(models.Context(project_id))
    if topic_name not in topics:
      raise RuntimeError(
          f'Topic {topic_name} for Subscription {self.name} not found')
    return topics[topic_name]

  def is_detached(self) -> bool:
    """Return if subscription is detached."""
    if 'detached' in self._resource_data:
      return bool(self._resource_data['detached'])
    return False

  def is_big_query_subscription(self) -> bool:
    """Return Boolean value if subscription is a big query subscription."""
    if 'bigqueryConfig' in self._resource_data:
      return True
    return False

  def is_gcs_subscription(self) -> bool:
    """Return Boolean value if subscription is a gcs subscription."""
    if 'cloudStorageConfig' in self._resource_data:
      return True
    return False

  def is_push_subscription(self) -> bool:
    """Return Boolean value if subscription is a push subscription."""
    if (self._resource_data['pushConfig'] or self.is_big_query_subscription() or
        self.is_gcs_subscription()):
      return True
    return False

  def has_dead_letter_topic(self) -> bool:
    """Return Truthy value if subscription has a dead-letter topic."""
    if 'deadLetterPolicy' in self._resource_data:
      return bool(self._resource_data['deadLetterPolicy']['deadLetterTopic'])
    return False

  def gcs_subscription_bucket(self) -> str:
    """Return the name of the bucket attached to GCS subscription."""
    if self.is_gcs_subscription():
      return get_path(self._resource_data, ('cloudStorageConfig', 'bucket'))
    return ''  # acts as a null return that can be evaluated as a falsy value


@caching.cached_api_call
def get_subscriptions(context: models.Context) -> Mapping[str, Subscription]:
  subscriptions: Dict[str, Subscription] = {}
  if not apis.is_enabled(context.project_id, 'pubsub'):
    return subscriptions
  pubsub_api = apis.get_api('pubsub', 'v1', context.project_id)
  logging.info('fetching list of PubSub subscriptions in project %s',
               context.project_id)
  query = pubsub_api.projects().subscriptions().list(
      project=f'projects/{context.project_id}')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'subscriptions' not in resp:
      return subscriptions
    for s in resp['subscriptions']:
      # verify that we have some minimal data that we expect
      if 'name' not in s:
        raise RuntimeError('missing data in topics response')

      # projects/{project}/subscriptions/{sub}
      result = re.match(r'projects/[^/]+/subscriptions/([^/]+)', s['name'])
      if not result:
        logging.error('invalid subscription data: %s', s['name'])
        continue

      if not context.match_project_resource(resource=result.group(1),
                                            labels=s.get('labels', {})):
        continue

      subscriptions[s['name']] = Subscription(project_id=context.project_id,
                                              resource_data=s)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return subscriptions


class SubscriptionIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_subscription_iam_policy(name: str) -> SubscriptionIAMPolicy:
  project_id = utils.get_project_by_res_name(name)

  pubsub_api = apis.get_api('pubsub', 'v1', project_id)
  request = pubsub_api.projects().subscriptions().getIamPolicy(resource=name)

  return iam.fetch_iam_policy(request, SubscriptionIAMPolicy, project_id, name)
