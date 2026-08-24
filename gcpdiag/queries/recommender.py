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
"""Queries related to Google Cloud Recommender."""

import logging
from typing import List

import googleapiclient.errors

from gcpdiag import caching, models, utils
from gcpdiag.queries import apis, apis_utils


class Recommendation(models.Resource):
  """Represents a Recommender Recommendation.

  See also the API documentation:
  https://cloud.google.com/recommender/docs/reference/rest/v1/projects.locations.recommenders.recommendations
  """

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    return self.name

  @property
  def description(self) -> str:
    return self._resource_data.get('description', '')

  @property
  def recommender_subtype(self) -> str:
    return self._resource_data.get('recommenderSubtype', '')

  @property
  def state(self) -> str:
    return self._resource_data.get('stateInfo', {}).get('state', '')

  @property
  def target_resources(self) -> List[str]:
    return self._resource_data.get('targetResources', [])

  @property
  def content(self) -> dict:
    return self._resource_data.get('content', {})

  @property
  def primary_impact(self) -> dict:
    return self._resource_data.get('primaryImpact', {})


@caching.cached_api_call
def get_recommendations(
  context: models.Context,
  recommender_id: str,
  location: str = '-',
) -> List[Recommendation]:
  """Get a list of Recommendations for a given recommender in a project, caching the result."""
  recommendations: List[Recommendation] = []
  project_id = context.project_id
  if not apis.is_enabled(project_id, 'recommender'):
    return recommendations

  api = apis.get_api('recommender', 'v1', project_id)
  parent = f'projects/{project_id}/locations/{location}/recommenders/{recommender_id}'
  logging.debug('fetching recommendations for %s in location %s', recommender_id, location)

  try:
    for rec in apis_utils.list_all(
      request=api.projects().locations().recommenders().recommendations().list(parent=parent),
      next_function=api.projects().locations().recommenders().recommendations().list_next,
      response_keyword='recommendations',
    ):
      recommendations.append(Recommendation(project_id, rec))
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return recommendations
