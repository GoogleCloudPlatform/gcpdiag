# Lint as: python3
"""Test code in gke.py."""
import gke


class TestCluster:

  def test_get_full_path(self):
    cluster = gke.Cluster(
        project_id='abc', location='europe-west1', name='foobar')
    assert (cluster.get_full_path() ==
            '/projects/abc/locations/europe-west1/clusters/foobar')
