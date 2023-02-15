#
# Copyright 2021 Google LLC
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
"""Orphaned YARN application!

This rule will look if any Orphaned YARN application are killed by dataproc
agent in the cluster.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

CLASS_NAME = 'com.google.cloud.hadoop.services.agent.job.YarnJobUpdater'
MATCH_STR = 'Killing orphaned yarn application'
RESOURCE_TYPE = 'cloud_dataproc_cluster'

# Criteria to filter for logs
LOG_FILTER = ['severity=ERROR', f'jsonPayload.message=~"{MATCH_STR}"']

logs_by_project = {}
clusters_by_project = set()


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type=RESOURCE_TYPE,
      log_name='log_id("google.dataproc.agent")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  clusters = dataproc.get_clusters(context)
  name_to_cluster = {cluster.name: cluster for cluster in clusters}

  if not clusters:
    report.add_skipped(project, 'no clusters found')
    return

  logs_entries = logs_by_project[context.project_id]
  entries = logs_entries.entries
  for log_entry in entries:
    if (log_entry['severity'] != 'ERROR' or CLASS_NAME not in get_path(
        log_entry, ('jsonPayload', 'class'), default='') or
        MATCH_STR not in get_path(log_entry, ('jsonPayload', 'message'),
                                  default='')):
      continue

    cluster_name = get_path(log_entry, ('resource', 'labels', 'cluster_name'),
                            default='')

    if cluster_name:
      clusters_by_project.add(cluster_name)

  for cluster_name in clusters_by_project:
    report.add_failed(name_to_cluster[cluster_name], MATCH_STR)
  for cluster_name in name_to_cluster:
    if cluster_name not in name_to_cluster:
      report.add_ok(name_to_cluster[cluster_name])
