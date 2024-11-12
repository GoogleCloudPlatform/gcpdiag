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
"""GKE dual-stack with IPv6 enabled uses an internal IP address for the Internal LB

When using a GKE cluster with a dual-stack subnet and external IPv6 addresses,
creating or updating an internal load balancer service is not possible.  The
external IPv6 configuration forces the system to prioritize external IP addresses,
making internal IP addresses unavailable for the load balancer.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR = 'does not have internal IPv6 ranges, required for an internal IPv6 Service'

logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)

  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[context.project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_cluster',
        log_name='log_id("events")',
        filter_str=('severity="WARNING"' + ' AND ' +
                    f'jsonPayload.message:"{MATCH_STR}"'))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Skip entire rule if logging is disabled.
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

  bad_clusters = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)
  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_clusters:
      report.add_failed(c, logs.format_log_entry(bad_clusters[c]))
    else:
      report.add_ok(c)
