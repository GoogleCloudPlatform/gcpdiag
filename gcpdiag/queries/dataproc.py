# Copyright 2021 Google LLC
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
"""Queries related to Dataproc."""

from typing import Iterable, List

from gcpdiag import caching, config, models
from gcpdiag.lint import get_executor
from gcpdiag.queries import apis, gce


class Cluster(models.Resource):
  """ Represents Dataproc Cluster """
  name: str
  region: str
  status: str

  def __init__(self, name: str, status: str, project_id: str, region: str):
    super().__init__(project_id)
    self.name = name
    self.region = region
    self.status = status

  def is_running(self) -> bool:
    return self.status == 'RUNNING'

  @property
  def full_path(self) -> str:
    return f'projects/{self.project_id}/regions/{self.region}/clusters/{self.name}'

  @property
  def short_path(self) -> str:
    return f'{self.project_id}/{self.region}/{self.name}'

  def __str__(self) -> str:
    return self.short_path


class Region:
  """ Represents Dataproc region """
  project_id: str
  region: str

  def __init__(self, project_id: str, region: str):
    self.project_id = project_id
    self.region = region

  def get_clusters(self) -> Iterable[Cluster]:
    r = []
    for cluster in self.query_api():
      r.append(
          Cluster(name=cluster['clusterName'],
                  status=cluster['status']['state'],
                  project_id=self.project_id,
                  region=self.region))
    return r

  def query_api(self) -> Iterable[dict]:
    api = apis.get_api('dataproc', 'v1', self.project_id)
    query = api.projects().regions().clusters().list(projectId=self.project_id,
                                                     region=self.region)
    resp = query.execute(num_retries=config.API_RETRIES)
    return resp.get('clusters', [])


class Dataproc:
  """ Represents Dataproc product """
  project_id: str

  def __init__(self, project_id: str):
    self.project_id = project_id

  def get_regions(self) -> Iterable[Region]:
    return [
        Region(self.project_id, r) for r in gce.get_all_regions(self.project_id)
    ]

  def is_api_enabled(self) -> bool:
    return apis.is_enabled(self.project_id, 'dataproc')


@caching.cached_api_call
def get_clusters(context: models.Context) -> Iterable[Cluster]:
  r: List[Cluster] = []
  dataproc = Dataproc(context.project_id)
  if not dataproc.is_api_enabled():
    return r
  executor = get_executor()
  for clusters in executor.map(lambda r: r.get_clusters(),
                               dataproc.get_regions()):
    r += clusters
  return r
