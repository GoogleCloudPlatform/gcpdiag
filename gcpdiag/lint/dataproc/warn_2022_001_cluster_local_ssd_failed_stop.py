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
"""Dataproc clusters are not failed to stop due to the local SSDs

You cannot stop clusters with local SSDs attached since it triggers shutdown to
the VM. However, if you do shut down a VM using local SSDs, then you can't
start the VM again later, and the data on the local SSD is lost.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

METHOD_NAME = 'google.cloud.dataproc.v1.ClusterController.StopCluster'
MATCH_STR = 'Clusters that have local SSDs cannot be stopped.'

LOG_FILTER = [
    'severity=ERROR', f'protoPayload.methodName="{METHOD_NAME}"',
    f'protoPayload.status.message:"{MATCH_STR}"'
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_dataproc_cluster',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
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

  failed_to_stop_clusters = []

  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for log_entry in logs_by_project[context.project_id].entries:
      # Filter out non-relevant log entries.
      if log_entry['severity'] != 'ERROR' or \
         METHOD_NAME not in get_path(log_entry,
                     ('protoPayload', 'methodName'), default='') or \
         MATCH_STR not in get_path(log_entry,
                     ('protoPayload', 'status', 'message'), default=''):
        continue

      cluster_name = get_path(log_entry,
                              ('protoPayload', 'request', 'clusterName'),
                              default='')
      if cluster_name and cluster_name not in failed_to_stop_clusters:
        failed_to_stop_clusters.append(cluster_name)

  for cluster_name in failed_to_stop_clusters:
    report.add_failed(name_to_cluster[cluster_name],
                      'failed to stop due to local SSDs')
  for cluster_name in [
      cluster_name for cluster_name in name_to_cluster
      if cluster_name not in failed_to_stop_clusters
  ]:
    report.add_ok(name_to_cluster[cluster_name])
