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
"""Test code in managedkafka.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, managedkafka

DUMMY_PROJECT_NAME = 'gcpdiag-managedkafka1-aaaa'
DUMMY_CLUSTER_NAME = (
  'projects/gcpdiag-managedkafka1-aaaa/locations/us-central1/clusters/gcpdiag-my-kafka-cluster'
)
DUMMY_TOPIC_NAME = 'projects/gcpdiag-managedkafka1-aaaa/locations/us-central1/clusters/gcpdiag-my-kafka-cluster/topics/gcpdiag-my-topic'
DUMMY_GROUP_NAME = 'projects/gcpdiag-managedkafka1-aaaa/locations/us-central1/clusters/gcpdiag-my-kafka-cluster/consumerGroups/gcpdiag-my-group'
DUMMY_ACL_NAME = 'projects/gcpdiag-managedkafka1-aaaa/locations/us-central1/clusters/gcpdiag-my-kafka-cluster/acls/gcpdiag-my-acl'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestManagedKafka:
  """Test Managed Kafka Queries."""

  def test_get_clusters(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = managedkafka.get_clusters(context=context)
    assert DUMMY_CLUSTER_NAME in clusters
    assert clusters[DUMMY_CLUSTER_NAME].name == 'gcpdiag-my-kafka-cluster'
    assert clusters[DUMMY_CLUSTER_NAME].state == 'ACTIVE'
    assert clusters[DUMMY_CLUSTER_NAME].location == 'us-central1'

  def test_get_cluster(self):
    cluster = managedkafka.get_cluster(
      project_id=DUMMY_PROJECT_NAME,
      location='us-central1',
      cluster_name='gcpdiag-my-kafka-cluster',
    )
    assert cluster is not None
    assert cluster.full_path == DUMMY_CLUSTER_NAME
    assert cluster.state == 'ACTIVE'
    assert len(cluster.broker_details) == 3
    assert cluster.broker_details[0]['brokerIndex'] == 0
    assert cluster.broker_details[0]['rack'] == 'us-central1-a'

  def test_get_topics(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    topics = managedkafka.get_topics(context=context, cluster_name=DUMMY_CLUSTER_NAME)

    # Verify user topic
    assert DUMMY_TOPIC_NAME in topics
    assert topics[DUMMY_TOPIC_NAME].name == 'gcpdiag-my-topic'
    assert topics[DUMMY_TOPIC_NAME].partition_count == 30
    assert topics[DUMMY_TOPIC_NAME].configs['min.insync.replicas'] == '2'
    assert topics[DUMMY_TOPIC_NAME].is_internal is False

    # Verify internal topic
    internal_topic_path = f'{DUMMY_CLUSTER_NAME}/topics/__internal_google_managed_kafka_topic_10'
    assert internal_topic_path in topics
    assert topics[internal_topic_path].name == '__internal_google_managed_kafka_topic_10'
    assert topics[internal_topic_path].is_internal is True

  def test_get_topic(self):
    topic = managedkafka.get_topic(
      project_id=DUMMY_PROJECT_NAME,
      location='us-central1',
      cluster_name='gcpdiag-my-kafka-cluster',
      topic_name='gcpdiag-my-topic',
    )
    assert topic is not None
    assert topic.name == 'gcpdiag-my-topic'
    assert topic.partition_count == 30

  def test_get_consumer_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    groups = managedkafka.get_consumer_groups(context=context, cluster_name=DUMMY_CLUSTER_NAME)
    assert DUMMY_GROUP_NAME in groups
    assert groups[DUMMY_GROUP_NAME].name == 'gcpdiag-my-group'
    assert groups[DUMMY_GROUP_NAME].state == 'STABLE'

  def test_get_consumer_group(self):
    group = managedkafka.get_consumer_group(
      project_id=DUMMY_PROJECT_NAME,
      location='us-central1',
      cluster_name='gcpdiag-my-kafka-cluster',
      group_name='gcpdiag-my-group',
    )
    assert group is not None
    assert group.name == 'gcpdiag-my-group'
    assert group.state == 'STABLE'

  def test_get_acls(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    acls = managedkafka.get_acls(context=context, cluster_name=DUMMY_CLUSTER_NAME)
    assert DUMMY_ACL_NAME in acls
    assert acls[DUMMY_ACL_NAME].name == 'gcpdiag-my-acl'
    assert len(acls[DUMMY_ACL_NAME].acl_entries) == 1
    assert acls[DUMMY_ACL_NAME].acl_entries[0]['principal'] == 'User:alice@example.com'

  def test_get_acl(self):
    acl = managedkafka.get_acl(
      project_id=DUMMY_PROJECT_NAME,
      location='us-central1',
      cluster_name='gcpdiag-my-kafka-cluster',
      acl_name='gcpdiag-my-acl',
    )
    assert acl is not None
    assert acl.name == 'gcpdiag-my-acl'
    assert len(acl.acl_entries) == 1
