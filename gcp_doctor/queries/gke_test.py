# Lint as: python3
"""Test code in gke.py."""

import ipaddress
from unittest import mock

from gcp_doctor import models
from gcp_doctor.queries import gke, gke_stub

DUMMY_PROJECT_NAME = 'gcpd-gke-1-9b90'
DUMMY_CLUSTER1_NAME = f'projects/{DUMMY_PROJECT_NAME}/zones/europe-west4-a/clusters/gke1'
DUMMY_CLUSTER1_LABELS = {'foo': 'bar'}
DUMMY_CLUSTER2_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west1/clusters/gke2'
DUMMY_CLUSTER2_SHORT_NAME = f'{DUMMY_PROJECT_NAME}/europe-west1/gke2'


@mock.patch('gcp_doctor.queries.apis.get_api', new=gke_stub.get_api_stub)
class TestCluster:
  """Test gke.Cluster."""

  def test_get_clusters_by_label(self):
    """get_clusters returns the right cluster matched by label."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_CLUSTER1_LABELS])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters and len(clusters) == 1

  def test_get_clusters_by_region(self):
    """get_clusters returns the right cluster matched by region."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             regions=['europe-west4'])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters and len(clusters) == 1

  def test_get_path_regional(self):
    """get_full_path and get_short_path should return correct results with regional clusters."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.get_full_path() == DUMMY_CLUSTER2_NAME
    assert str(c) == DUMMY_CLUSTER2_NAME
    assert c.get_short_path() == DUMMY_CLUSTER2_SHORT_NAME

  def test_has_logging_enabled_false(self):
    """has_logging_enabled should return false for GKE cluster with logging disabled."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_logging_enabled()

  def test_has_logging_enabled_true(self):
    """has_logging_enabled should return true for GKE cluster with logging enabled."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.has_logging_enabled()

  def test_has_default_service_account(self):
    """has_default_service_account should return true for GKE node-pools with
    the default GCE SA."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    # 'default-pool' has the default SA
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.nodepools[0].has_default_service_account()
    # 'default-pool' doesn't have the default SA
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert not c.nodepools[0].has_default_service_account()

  def test_pod_ipv4_cidr(self):
    """returns correct pod CIDR"""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.pod_ipv4_cidr.compare_networks(
        ipaddress.ip_network('192.168.1.0/24')) == 0
    # cluster 2
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.pod_ipv4_cidr.compare_networks(
        ipaddress.ip_network('10.112.0.0/14')) == 0

  def test_current_node_count(self):
    """returns correct number of nodes running"""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.current_node_count == 1
    # cluster 2
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.current_node_count == 3

  def test_np_pod_ipv4_cidr_size(self):
    """resturn correct pod CIDR size per allocated to node pool."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.nodepools[0].pod_ipv4_cidr_size == 24
