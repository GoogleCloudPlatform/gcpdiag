# Copyright 2025 Google LLC
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
"""If you're using a Google Kubernetes Engine (GKE) cluster with a

dual-stack subnet configured for internal IPv6 access, you won't
be able to create or update an external load balancer service.

External load balancers need an external IP address. This address is normally
taken from the GKE subnet.

Internal IPv6 access prevents external IP allocation. When your subnet is
setup for internal IPv6 access, the system prioritizes internal IPs, making it
impossible to get an external IPv6 address for the load balancer.

This limitation applies to services without the annotation
"networking.gke.io/load-balancer-type: "Internal", which specifically instructs
GKE to create an external load balancer.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR_1 = 'Error ensuring Resource for L4 External LoadBalancer, err: subnet'
MATCH_STR_2 = 'does not have external IPv6 ranges, required for an external IPv6 Service'
MATCH_STR_3 = 'You can specify an external IPv6 subnet using the'

logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_cluster',
        log_name='log_id("events")',
        filter_str=(f'jsonPayload.message=~"{MATCH_STR_1}" AND '
                    f'jsonPayload.message=~"{MATCH_STR_2}" AND '
                    f'jsonPayload.message=~"{MATCH_STR_3}" '),
    )


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
      if MATCH_STR_2 in log_entry['jsonPayload']['message']:
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
