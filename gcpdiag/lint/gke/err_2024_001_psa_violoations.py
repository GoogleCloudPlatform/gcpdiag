# Copyright 2024 Google LLC
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
"""Checking for no Pod Security Admission violations in the project.

Verify that there are no PSA violations in any namespace of any cluster in the
project.
If there are any violations inspect the logs to find what caused the violation
and if required adjust the policy or pod manifest.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

_MATCH_STR = 'Forbidden'
_LOG_RESOURCE_TYPE = 'k8s_cluster'
_LOG_NAME = 'log_id("cloudaudit.googleapis.com/activity")'
_LOG_FILTER_STR = ('severity=DEFAULT AND ' +
                   'protoPayload.response.message:"violates PodSecurity"')

logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type=_LOG_RESOURCE_TYPE,
        log_name=_LOG_NAME,
        filter_str=_LOG_FILTER_STR,
    )


def _filter_f(log_entry):
  try:
    return _MATCH_STR in log_entry['protoPayload']['response']['reason']
  except KeyError:
    return False


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  clusters = gke.get_clusters(context)

  # Check: if no projects then skip
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Check for Forbidden logs
  bad_pods_by_cluster = util.gke_logs_find_bad_pods(
      context=context, logs_by_project=logs_by_project, filter_f=_filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_pods_by_cluster:
      report.add_failed(
          c,
          'PodSecurity Admission policy violation identified for pods:\n. ' +
          '\n. '.join(bad_pods_by_cluster[c]),
      )
    else:
      report.add_ok(c)
