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
"""Dataproc cluster is in RUNNING state

Cluster should normally spend most of the time in RUNNING state.
"""

from gcpdiag import lint, models
from gcpdiag.queries import dataproc

clusters_by_project = {}


def prefetch_rule(context: models.Context):
  clusters_by_project[context.project_id] = dataproc.get_clusters(context)


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:
  # clusters = dataproc.get_clusters(context)
  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no dataproc clusters found')

  for cluster in clusters:
    if cluster.is_running():
      report.add_ok(cluster)
    else:
      report.add_failed(cluster)
