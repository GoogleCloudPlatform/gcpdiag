# Copyright 2023 Google LLC
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
"""Vertex AI Feature Store has a known state

Vertex AI featurestores should have a known state
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, vertex

featurestores_by_project = {}


def prefetch_rule(context: models.Context):
  featurestores_by_project[context.project_id] = vertex.get_featurestores(
      context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  if not apis.is_enabled(context.project_id, 'aiplatform'):
    report.add_skipped(None, 'Vertex API is disabled')
    return

  featurestores = featurestores_by_project[context.project_id]

  if not featurestores:
    report.add_skipped(None, 'No featurestores found')
    return

  for featurestore in featurestores.values():
    state = vertex.FeaturestoreStateEnum.STATE_UNSPECIFIED
    if featurestore.state:
      state = vertex.FeaturestoreStateEnum(featurestore.state)
    if state != vertex.FeaturestoreStateEnum.STATE_UNSPECIFIED:
      report.add_ok(featurestore)
    else:
      state_message = f'Featurestore state is unknown. State = {state}'
      report.add_failed(featurestore, state_message)
