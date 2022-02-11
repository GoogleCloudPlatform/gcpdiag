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
"""Test code in pubsub.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, pubsub

DUMMY_PROJECT_NAME = 'gcpdiag-pubsub1-aaaa'
DUMMY_TOPIC_NAME = 'projects/gcpdiag-pubsub1-aaaa/topics/gcpdiag-pubsub1topic-aaaa'
DUMMY_SUB_NAME = 'projects/gcpdiag-pubsub1-aaaa/subscriptions/gcpdiag-pubsub1subscription-aaaa'
DUMMY_PERM = 'domain:google.com'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestPubsub:
  """Test Pubsub"""

  def test_get_topics(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    topics = pubsub.get_topics(context=context)
    assert DUMMY_TOPIC_NAME in topics

  def test_get_subscription(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    subscription = pubsub.get_subscription(context=context)
    assert DUMMY_SUB_NAME in subscription

  def test_get_topic_iam_policy(self):
    policy = pubsub.get_topic_iam_policy(DUMMY_TOPIC_NAME)
    assert DUMMY_PERM in policy.get_members()

  def test_get_subscription_iam_policy(self):
    policy = pubsub.get_subscription_iam_policy(DUMMY_SUB_NAME)
    assert DUMMY_PERM in policy.get_members()
