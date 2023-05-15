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
"""Dataproc cluster has sufficient quota.

When creating a Dataproc cluster, the project must have available quotas for
the resources you request, such as CPU, disk, and IP addresses.
"""

import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

MATCH_STR = 'Insufficient .* quota'
RESOURCE_TYPE = 'cloud_dataproc_cluster'

# Criteria to filter for logs
LOG_FILTER = f"""
protoPayload.status.message=~("{MATCH_STR}")
severity=ERROR
"""

logs_by_project = {}
log_search_pattern = re.compile(MATCH_STR)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type=RESOURCE_TYPE,
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=LOG_FILTER,
  )


def format_cluster(cluster_name, uuid):
  return cluster_name + (f'(UUID: {uuid})' if uuid else '')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  clusters = dataproc.get_clusters(context)

  if not clusters:
    report.add_skipped(project, 'no clusters found')
    return

  failed_clusters = set()
  if logs_by_project.get(context.project_id):
    entries = logs_by_project[context.project_id].entries
    for log_entry in entries:
      msg = get_path(log_entry, ('protoPayload', 'status', 'message'),
                     default='')
      is_pattern_found = log_search_pattern.search(msg)
      # Filter out non-relevant log entries.
      if not (log_entry['severity'] == 'ERROR' and is_pattern_found):
        continue

      cluster_name = get_path(
          log_entry,
          ('resource', 'labels', 'cluster_name'),
          default='Unknown Cluster',
      )
      uuid = get_path(log_entry, ('resource', 'labels', 'cluster_uuid'),
                      default='')
      failed_clusters.add((cluster_name, uuid))

    if failed_clusters:
      report.add_failed(
          project,
          'The following clusters failed because of quota errors : {}'.format(
              ', '.join(
                  format_cluster(cluster_name, uuid)
                  for cluster_name, uuid in failed_clusters)),
      )
    else:
      report.add_ok(project)
  else:
    report.add_ok(project)
