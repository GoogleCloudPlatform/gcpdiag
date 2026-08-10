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
"""Test code in recommender.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, recommender

DUMMY_PROJECT_ID = 'gcpdiag-gke1-aaaa'
RECOMMENDER_ID = 'google.container.DiagnosisRecommender'
LOCATION = 'europe-west4'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestRecommendation:
  """Test Recommender query module."""

  def test_get_recommendations(self):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    recs = recommender.get_recommendations(
      context=context, recommender_id=RECOMMENDER_ID, location=LOCATION
    )
    assert len(recs) == 4

    rec1 = recs[0]
    assert rec1.name == (
      f'projects/{DUMMY_PROJECT_ID}/locations/{LOCATION}/recommenders/'
      f'{RECOMMENDER_ID}/recommendations/rec-pdb-1'
    )
    assert rec1.full_path == rec1.name
    assert rec1.recommender_subtype == 'GKE_WORKLOAD_PDB_MISSING'
    assert rec1.state == 'ACTIVE'
    assert 'Workload missing Pod Disruption Budget' in rec1.description
    assert len(rec1.target_resources) == 1
    assert 'gke2' in rec1.target_resources[0]
    assert 'overview' in rec1.content
    assert rec1.primary_impact == {'category': 'RELIABILITY'}

  def test_recommendation_default_properties(self):
    r = recommender.Recommendation(
      project_id=DUMMY_PROJECT_ID,
      resource_data={'name': ('projects/p/locations/l/recommenders/r/recommendations/rec-1')},
    )
    assert r.description == ''
    assert r.recommender_subtype == ''
    assert r.state == ''
    assert r.target_resources == []
    assert r.content == {}
    assert r.primary_impact == {}

  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=False)
  def test_disabled_api(self, mock_is_enabled):
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    recs = recommender.get_recommendations(
      context=context,
      recommender_id='disabled-recommender',
      location=LOCATION,
    )
    assert recs == []
