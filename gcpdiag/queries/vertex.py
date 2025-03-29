# Copyright 2023 Google LLC
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

# Lint as: python3
"""Queries related to GCP Vertex AI
"""

import enum
import logging
import re
from typing import Dict

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis

FEATURESTORES_KEY = 'featurestores'
NAME_KEY = 'name'
STATE_KEY = 'state'

REGIONS = {
    1: 'asia-east1',
    2: 'asia-east2',
    3: 'asia-northeast1',
    4: 'asia-northeast2',
    5: 'asia-northeast3',
    6: 'asia-south1',
    7: 'asia-south2',
    8: 'asia-southeast1',
    9: 'asia-southeast2',
    10: 'australia-southeast1',
    11: 'australia-southeast2',
    12: 'europe-central2',
    13: 'europe-north1',
    14: 'europe-southwest1',
    15: 'europe-west1',
    16: 'europe-west2',
    17: 'europe-west3',
    18: 'europe-west4',
    19: 'europe-west6',
    20: 'europe-west8',
    21: 'europe-west9',
    22: 'europe-west12',
    23: 'me-central1',
    24: 'me-west1',
    25: 'northamerica-northeast1',
    26: 'northamerica-northeast2',
    27: 'southamerica-east1',
    28: 'southamerica-west1',
    29: 'us-central1',
    30: 'us-east1',
    31: 'us-east4',
    32: 'us-east5',
    33: 'us-south1',
    34: 'us-west1',
    35: 'us-west2',
    36: 'us-west3',
    37: 'us-west4',
}

# Different Vertex AI features available in different regions
FEATURE_REGIONS = {
    FEATURESTORES_KEY: [
        1, 2, 3, 5, 6, 8, 9, 10, 12, 15, 16, 17, 18, 19, 21, 25, 26, 27, 29, 30,
        31, 34, 35, 36, 37
    ]
}


class FeaturestoreStateEnum(enum.Enum):
  """The possible states a Vertex AI featurestore can have.

  https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.featurestores#state
  """

  STATE_UNSPECIFIED = 'STATE_UNSPECIFIED'
  STABLE = 'STABLE'
  UPDATING = 'UPDATING'

  def __str__(self):
    return str(self.value)


class Featurestore(models.Resource):
  """Represent a Vertex AI featurestore

  https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.featurestores#resource:-featurestore
  """

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """
    The 'name' of the featurestore is already in the full path form
    projects/{project}/locations/{location}/featurestores/{featurestore}.
    """
    return self._resource_data[NAME_KEY]

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/featurestores/', '/', path)
    return path

  @property
  def name(self) -> str:
    logging.debug(self._resource_data)
    return self._resource_data[NAME_KEY]

  @property
  def state(self) -> str:
    logging.debug(self._resource_data)
    return self._resource_data[STATE_KEY]


@caching.cached_api_call
def get_featurestores(context: models.Context) -> Dict[str, Featurestore]:
  featurestores: Dict[str, Featurestore] = {}
  if not apis.is_enabled(context.project_id, 'aiplatform'):
    return featurestores
  for region in FEATURE_REGIONS[FEATURESTORES_KEY]:
    featurestores_res: Dict[str, Featurestore] = {}
    region_name = REGIONS[region]
    logging.debug(
        'fetching list of Vertex AI featurestores in project %s for region %s',
        context.project_id, region_name)
    vertex_api = apis.get_api('aiplatform', 'v1', context.project_id,
                              region_name)
    query = vertex_api.projects().locations().featurestores().list(
        parent=f'projects/{context.project_id}/locations/{region_name}')
    try:
      resp = query.execute(num_retries=config.API_RETRIES)
      if FEATURESTORES_KEY not in resp:
        continue
      for resp_i in resp[FEATURESTORES_KEY]:
        # verify that we have some minimal data that we expect
        if NAME_KEY not in resp_i:
          raise RuntimeError(
              'missing featurestore name in projects.locations.featurestores.list response'
          )
        i = Featurestore(project_id=context.project_id, resource_data=resp_i)
        featurestores_res[i.full_path] = i
        if featurestores:
          featurestores.update(featurestores_res)
        else:
          featurestores = featurestores_res
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err
  return featurestores
