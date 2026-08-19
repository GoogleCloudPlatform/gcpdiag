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
"""GKE ingresses are well configured.

Verify that the Google Kubernetes Engine ingresses are well configured.
This rule inspects cluster events for ingress configuration errors.
"""

from gcpdiag.queries import gke, logs

logs_by_project = {}


def prepare_rule(context):
  """Query Cloud Logging for ingress errors."""
  clusters = gke.get_clusters(context)

  # Ask Cloud Logging for the GKE Ingress error diaries (events)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
      project_id=project_id,
      resource_type='k8s_cluster',
      log_name='log_id("events")',
      filter_str=(
        '(jsonPayload.source.component="l7-lb-controller" OR '
        'jsonPayload.source.component="loadbalancer-controller") '
        'severity>=WARNING'
      ),
    )


def run_rule(context, report):
  """Check cluster events against query results."""
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    failed = False
    message = ''

    # Look through logs to see if this specific cluster had errors
    if c.project_id in logs_by_project:
      for log_entry in logs_by_project[c.project_id].entries:
        # Ensure the log entry belongs to the cluster we are currently checking
        if log_entry['resource']['labels'].get('cluster_name') == c.name:
          failed = True
          # Extract the exact complaint from the GKE Ingress Controller
          message += (
            log_entry.get('jsonPayload', {}).get(
              'message', 'Ingress configuration error detected in logs.'
            )
            + '\n'
          )
    if not failed:
      report.add_ok(c)
    else:
      report.add_failed(c, message[:-1])
