# Lint as: python3
"""Mock functionality of gke.py for testing."""

from gcp_doctor.queries import gke


class Cluster(gke.Cluster):

  def has_monitoring_enabled(self) -> bool:
    return 0
