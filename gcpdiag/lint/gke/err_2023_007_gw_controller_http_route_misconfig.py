# Copyright 2023 Google LLC
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
"""GKE Gateway controller reporting invalid HTTPRoute for Gateway

Gateway controller creates urls maps based on HTTPRoute resources.
If the HTTP route has invalid reference to gateway or invalid spec,
controller will not be able create url maps.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR = 'Error GWCER106: Gateway'
logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_cluster',
        log_name='log_id("events")',
        filter_str=f'jsonPayload.message:"{MATCH_STR}"',
    )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Skip entire rule if Cloud Logging is disabled
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
      if MATCH_STR in log_entry['jsonPayload']['message']:
        return True
    except KeyError:
      return False

  bad_nodes_by_cluster = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)

  # Create the report
  for _, c in sorted(clusters.items()):
    if c in bad_nodes_by_cluster:
      report.add_failed(c)
    else:
      report.add_ok(c)
