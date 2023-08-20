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
"""Test code in vertex.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, vertex

DUMMY_PROJECT_NAME = 'gcpdiag-vertex1-aaaa'
DUMMY_PROJECT_NUMBER = '12340015'
DUMMY_FEATURESTORE_NAME = 'gcpdiag_vertex1featurestore_aaaa'
DUMMY_FEATURESTORE_FULL_PATH_NAME = \
  f'projects/{DUMMY_PROJECT_NUMBER}/locations/us-west1/featurestores/{DUMMY_FEATURESTORE_NAME}'
DUMMY_PERM = 'domain:google.com'
DUMMY_FEATURESTORE_STATE = vertex.FeaturestoreStateEnum('STATE_UNSPECIFIED')


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestVertex:
  """Test Vertex AI Featurestores"""

  def test_get_featurestores(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    featurestores = vertex.get_featurestores(context=context)
    assert DUMMY_FEATURESTORE_FULL_PATH_NAME in featurestores
