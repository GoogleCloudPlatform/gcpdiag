#
# Copyright 2022 Google LLC
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
"""Dataproc cluster firewall rules for connectivity between master and worker nodes established!

The master node needs to communicate with the worker nodes during cluster
creation. Sometimes VM to VM communications are blocked by firewall rules.
"""

import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

MATCH_STR = 'This usually happens when VM to VM communications are blocked'

RESOURCE_TYPE = 'cloud_dataproc_cluster'

contains_required_pattern = re.compile(MATCH_STR)

# Criteria to filter for logs
LOG_FILTER = ['severity=ERROR', f'protoPayload.status.message=~"{MATCH_STR}"']

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type=RESOURCE_TYPE,
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  clusters = dataproc.get_clusters(context)

  if not clusters:
    report.add_skipped(project, 'no clusters found')
    return

  failed_clusters = set()
  if (logs_by_project.get(context.project_id) and
      logs_by_project[context.project_id].entries):
    for log_entry in logs_by_project[context.project_id].entries:
      msg = get_path(log_entry, ('protoPayload', 'status', 'message'),
                     default='')

      contains_required = contains_required_pattern.search(msg)

      # Filter out non-relevant log entries.
      if not (log_entry['severity'] == 'ERROR' and contains_required):
        continue

      entry_clusters = get_path(
          log_entry,
          ('resource', 'labels', 'cluster_name'),
          default='Unknown Cluster',
      )
      failed_clusters.add(entry_clusters)

    if failed_clusters:
      report.add_failed(
          project,
          'The following clusters failed : {}'.format(
              ', '.join(failed_clusters)),
      )
    else:
      report.add_ok(project)
  else:
    report.add_ok(project)
