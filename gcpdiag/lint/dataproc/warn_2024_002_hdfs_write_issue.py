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
"""HDFS can write file(s) to DataNode(s).

HDFS had issues writing file(s) to DataNode(s).
"""

import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, dataproc, logs

RE_PATTERN = (
    '(.*could only be written to .*are excluded in this operation.*)|'
    '(.*could only be replicated to .*are excluded in this operation.*)')

LOG_NAME = 'hadoop-hdfs-namenode'
SEVERITY = 'DEFAULT'
LOG_FILTER = [f'severity="{SEVERITY}"', f'jsonPayload.message=~"{RE_PATTERN}"']

MSG_RE = re.compile(RE_PATTERN)

logs_by_project = {}
clusters_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_dataproc_cluster',
      log_name=f'log_id("{LOG_NAME}")',
      filter_str=' AND '.join(LOG_FILTER),
  )


def prefetch_rule(context: models.Context):
  clusters_by_project[context.project_id] = dataproc.get_clusters(context)


def is_relevant(entry, context):
  return all([
      get_path(entry,
               ('resource', 'labels', 'project_id')) == context.project_id,
      get_path(entry, ('resource', 'type')) == 'cloud_dataproc_cluster',
      get_path(entry,
               'logName') == f'projects/{context.project_id}/logs/{LOG_NAME}',
      MSG_RE.match(get_path(entry, ('jsonPayload', 'message'))),
  ])


def get_clusters_having_relevant_log_entries(context):
  return {
      get_path(e, ('resource', 'labels', 'cluster_name'), default=None)
      for e in logs_by_project[context.project_id].entries
      if is_relevant(e, context)
  }


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """RUN the rule."""
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  clusters_with_issues = get_clusters_having_relevant_log_entries(context)

  for cluster in clusters_by_project[context.project_id]:
    if cluster.name in clusters_with_issues:
      report.add_failed(
          cluster,
          'HDFS could not write file(s) to DataNode(s).',
      )
    else:
      report.add_ok(cluster)
