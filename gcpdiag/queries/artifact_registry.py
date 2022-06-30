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
"""Queries related to GCP Artifact Registry

"""

from gcpdiag import caching
from gcpdiag.queries import apis, iam


class ArtifactRegistryIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_registry_iam_policy(project_id: str, location: str,
                            registry_name: str) -> ArtifactRegistryIAMPolicy:
  ar_api = apis.get_api('artifactregistry', 'v1', project_id)
  registry_id = 'projects/{}/locations/{}/repositories/{}'.format(
      project_id, location, registry_name)
  request = ar_api.projects().locations().repositories().getIamPolicy(
      resource=registry_id)
  return iam.fetch_iam_policy(request, ArtifactRegistryIAMPolicy, project_id,
                              registry_id)
