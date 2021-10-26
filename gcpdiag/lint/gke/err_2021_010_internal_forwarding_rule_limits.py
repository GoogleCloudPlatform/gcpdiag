# Copyright 2021 Google LLC
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
"""Check internal peering forwarding limits which affect GKE.

Internal Load Balancer creation can fail due to VPC internal forwarding rules limits.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import gke, logs

MATCH_STR_1 = 'INTERNAL_FORWARDING_RULES_WITH_PEERING_LIMITS_EXCEEDED'
MATCH_STR_2 = 'SyncLoadBalancerFailed'
logs_by_project = {}


def prepare_rule(context: models.Context):
  global logs_by_project
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_cluster',
      log_name='log_id("events")',
      filter_str=
      f'jsonPayload.message:"{MATCH_STR_1}" AND jsonPayload.reason:"{MATCH_STR_2}"'
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

    # Search the logs.
  def filter_f(log_entry):
    try:
      if (MATCH_STR_1 in log_entry['jsonPayload']['message']) and (
          MATCH_STR_2 in log_entry['jsonPayload']['reason']):
        return True
    except KeyError:
      return False

  bad_cluster = util.gke_logs_find_bad_cluster(context=context,
                                               logs_by_project=logs_by_project,
                                               filter_f=filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_cluster:
      report.add_failed(c, 'Quota issues for ILB :\n. ' + bad_cluster[c])
    else:
      report.add_ok(c)
