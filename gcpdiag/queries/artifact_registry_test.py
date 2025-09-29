# Copyright 2022 Google LLC
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
"""Test code in artifact_registry.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, artifact_registry

DUMMY_PROJECT_NAME = 'gcpdiag-gcb1-aaaa'
DUMMY_REGISTRY_ID = 'gcb1-repository'
DUMMY_REGISTRY_LOCATION = 'us-central1'
DUMMY_POLICY_MEMBER = 'serviceAccount:gcb-custom2@gcpdiag-gcb1-aaaa.iam.gserviceaccount.com'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestArtifactRegistry:
  """Test Artifact Registry."""

  def test_get_bucket_iam_policy(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    policy = artifact_registry.get_registry_iam_policy(context,
                                                       DUMMY_REGISTRY_LOCATION,
                                                       DUMMY_REGISTRY_ID)
    assert set(policy.get_members()) == {DUMMY_POLICY_MEMBER}

  def test_get_project_settings(self):
    settings = artifact_registry.get_project_settings(DUMMY_PROJECT_NAME)
    assert settings == artifact_registry.ProjectSettings(legacy_redirect=True)
