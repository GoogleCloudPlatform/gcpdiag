# Lint as: python3
"""Test code in gke.py."""

from unittest import mock

from gcp_doctor import models
from gcp_doctor.queries import gke, gke_stub

DUMMY_PROJECT_NAME = 'gcpd-gke-1-9b90'
DUMMY_CLUSTER1_NAME = f'projects/{DUMMY_PROJECT_NAME}/zones/europe-west4-a/clusters/gke1'
DUMMY_CLUSTER2_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west1/clusters/gke2'


@mock.patch('gcp_doctor.queries.apis.get_api', new=gke_stub.get_api_stub)
class TestCluster:
  """Test gke.Cluster."""

  def test_get_path_zonal(self):
    """get_full_path and get_short_path should return correct results with zonal clusters."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.get_full_path() == DUMMY_CLUSTER1_NAME
    assert c.get_short_path() == f'{DUMMY_PROJECT_NAME}/gke1'

  def test_get_path_regional(self):
    """get_full_path and get_short_path should return correct results with regional clusters."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.get_full_path() == DUMMY_CLUSTER2_NAME
    assert c.get_short_path() == f'{DUMMY_PROJECT_NAME}/gke2'

  def test_is_logging_enabled_true(self):
    """is_logging_enabled should return true for GKE cluster with logging enabled."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.is_logging_enabled()

  def test_is_logging_enabled_false(self):
    """is_logging_enabled should return false for GKE cluster with logging disabled."""
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert not c.is_logging_enabled()
