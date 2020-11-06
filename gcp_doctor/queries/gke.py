# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

import dataclasses

from gcp_doctor import models, utils


@dataclasses.dataclass
class Cluster(models.Resource):
  """Represents a GKE cluster."""
  location: str
  name: str

  def get_full_path(self) -> str:
    if utils.is_region(self.location):
      return (f'/projects/{self.project_id}/'
              f'locations/{self.location}/clusters/{self.name}')
    else:
      return (f'/projects/{self.project_id}/'
              f'zones/{self.location}/clusters/{self.name}')

  def get_short_path(self) -> str:
    return self.project_id + '/' + self.name

  def has_monitoring_enabled(self) -> bool:
    # FIXME(dwes)
    return False


#def get_clusters(context: models.Context):
#  container = get_api("container", "v1")
