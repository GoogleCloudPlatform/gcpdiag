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
"""Concurrent Job limit was not exceeded

If Dataproc agent is already running more than allowed concurrent job,
Dataproc job scheduling delays can be observed
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

CLASS_NAME = 'com.google.cloud.hadoop.services.agent.JobSubmissionLimiterImpl'
MATCH_STR = 'Too many running jobs'

LOG_FILTER = ['severity=WARNING', f'jsonPayload.message=~"{MATCH_STR}"']

logs_by_project = {}
clusters_by_project = []


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_dataproc_cluster',
      log_name='log_id("google.dataproc.agent")',
      filter_str=' AND '.join(LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  clusters = dataproc.get_clusters(context)
  name_to_cluster = {cluster.name: cluster for cluster in clusters}

  if not clusters:
    report.add_skipped(project, 'no clusters found')
    return


  if logs_by_project.get(context.project_id) and \
    logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'WARNING' or \
         CLASS_NAME not in get_path(log_entry,
                     ('jsonPayload', 'class'), default='') or \
         MATCH_STR not in get_path(log_entry,
                     ('jsonPayload',  'message'), default=''):
        continue

      cluster_name = get_path(log_entry, ('resource', 'labels', 'cluster_name'),
                              default='')

      if cluster_name and cluster_name not in clusters_by_project:
        clusters_by_project.append(cluster_name)

  for cluster_name in clusters_by_project:
    report.add_failed(name_to_cluster[cluster_name],
                      'Concurrent Job limit exceeded')
  for cluster_name in [
      cluster_name for cluster_name in name_to_cluster
      if cluster_name not in clusters_by_project
  ]:
    report.add_ok(name_to_cluster[cluster_name])
