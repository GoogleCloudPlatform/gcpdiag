# Lint as: python3

from gcp_doctor.queries import gke


class Cluster(gke.Cluster):

  def has_monitoring_enabled(self) -> bool:
    return 0
