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
"""GKE Webhook failures can seriously impact GKE Cluster.

Impact typically depends on the webhook failure policy and what type of GKE API
are handled by the webhook.

In some cases, a failing customer created webhook can render a cluster unusable
until corrected. Inability to create Pod (and similar)can lead to system pod not
getting scheduled / new pod not reaching a healthy state.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

_MATCH_STR_1 = 'failed calling webhook'
_MATCH_STR_2 = 'no endpoints available for service'

# gce_instance, cloudaudit.googleapis.com/activity
gke_logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    # k8s_cluster, api server logs
    gke_logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_cluster',
        log_name='log_id("cloudaudit.googleapis.com/activity")',
        filter_str=f'protoPayload.response.message:"{_MATCH_STR_1}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # skip entire rule if no logs found
  if not gke_logs_by_project:
    report.add_skipped(None, 'no logs found')
    return

  # Process gke_logs_by_project and search for failed webhook calls
  def filter_f(log_entry):
    try:
      if _MATCH_STR_1 in log_entry['protoPayload']['response']['message']:
        return bool(
            _MATCH_STR_2 in log_entry['protoPayload']['response']['message'])
    except KeyError:
      return False

  bad_clusters = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=gke_logs_by_project, filter_f=filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_clusters:
      report.add_failed(c, logs.format_log_entry(bad_clusters[c]))
    else:
      report.add_ok(c)
