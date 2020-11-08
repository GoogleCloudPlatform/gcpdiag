# Lint as: python3
"""Queries related to GCP Kubernetes Engine clusters."""

from typing import List

import googleapiclient.errors

from gcp_doctor import models, utils
from gcp_doctor.queries import apis


class Cluster(models.Resource):
  """Represents a GKE cluster.

  https://cloud.google.com/kubernetes-engine/docs/reference/rest/v1/projects.locations.clusters#Cluster
  """
  resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self.resource_data = resource_data

  @property
  def name(self) -> str:
    return self.resource_data['name']

  @property
  def location(self) -> str:
    return self.resource_data['location']

  def get_full_path(self) -> str:
    if utils.is_region(self.resource_data['location']):
      return (f'projects/{self.project_id}/'
              f'locations/{self.location}/clusters/{self.name}')
    else:
      return (f'projects/{self.project_id}/'
              f'zones/{self.location}/clusters/{self.name}')

  def get_short_path(self) -> str:
    return self.project_id + '/' + self.resource_data['name']


def get_clusters(context: models.Context) -> List[Cluster]:
  """Get a list of Cluster matching the given context."""
  # TODO: fix matching of region and labels
  clusters: List[Cluster] = []
  container_api = apis.get_api('container', 'v1')
  for project_id in context.projects:
    query = container_api.projects().locations().clusters().list(
        parent=f'projects/{project_id}/locations/-')
    try:
      resp = query.execute(num_retries=apis.RETRIES)
      if 'clusters' not in resp:
        raise RuntimeError(
            'clusters field missing in projects.locations.clusters.list response'
        )
      for resp_c in resp['clusters']:
        # verify that we some minimal data that we expect
        if 'name' not in resp_c or 'location' not in resp_c:
          raise RuntimeError(
              'missing data in projects.locations.clusters.list response')
        if not context.match_project_resource(
            location=resp_c('location'), labels=resp_c.get('resourceLabels')):
          continue
        c = Cluster(project_id=project_id, resource_data=resp_c)
        clusters.append(c)
    except googleapiclient.errors.HttpError as err:
      # TODO: implement proper exception classes
      errstr = utils.http_error_message(err)
      raise ValueError(
          f'can\'t list clusters for project {project_id}: {errstr}') from err
  return clusters
