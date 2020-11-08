# Lint as: python3
"""Test code in gke.py."""
import gke

TEST_CLUSTER = {
    'name': 'foobar',
    'location': 'europe-west1',
}


class TestCluster:
  """Test gke.Cluster."""

  def test_get_full_path_regional(self):
    cluster = gke.Cluster(project_id='abc', resource_data=TEST_CLUSTER)
    assert (cluster.get_full_path() ==
            'projects/abc/locations/europe-west1/clusters/foobar')

  def test_get_full_path_zonal(self):
    test_cluster_2 = TEST_CLUSTER.copy()
    test_cluster_2['location'] = 'europe-west1-b'
    cluster = gke.Cluster(project_id='abc', resource_data=test_cluster_2)
    assert (cluster.get_full_path() ==
            'projects/abc/zones/europe-west1-b/clusters/foobar')

  def test_get_short_path(self):
    cluster = gke.Cluster(project_id='abc', resource_data=TEST_CLUSTER)
    assert cluster.get_short_path() == 'abc/foobar'
