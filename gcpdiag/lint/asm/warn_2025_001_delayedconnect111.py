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
"""ASM: Envoy doesn't report connection failure

The error upstream_reset_before_response_started{remote_connection_failure,
delayed_connect_error:_111} occurs when Envoy fails to establish a connection with the
upstream service
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR_1 = (
    'upstream_reset_before_response_started{remote_connection_failure,'
    'delayed_connect_error:_111}')
MATCH_STR_2 = 'delayed connect error: 111'

logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_container',
        log_name='log_id("server-accesslog-stackdriver")',
        filter_str=(
            f'labels.response_details:"{MATCH_STR_1}" AND '
            f'labels.upstream_transport_failure_reason=~"{MATCH_STR_2}"'))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return
  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    # Search the logs.

  def filter_f(log_entry):
    try:
      if MATCH_STR_1 in log_entry['labels']['response_details']:
        if MATCH_STR_2 in log_entry['labels'][
            'upstream_transport_failure_reason']:
          return True
    except KeyError:
      return False

  bad_clusters = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)
  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_clusters:
      report.add_failed(c, logs.format_log_entry(bad_clusters[c]))
    else:
      report.add_ok(c)
