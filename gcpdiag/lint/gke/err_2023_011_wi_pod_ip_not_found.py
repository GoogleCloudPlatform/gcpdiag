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
"""GKE Metadata Server isn't reporting errors for pod IP not found.

The gke-metadata-server DaemonSet uses pod IP addresses to match client
requests to Kubernetes Service Accounts. Pod IP not found errors may indicate
a misconfiguration or a workload that is not compatible with GKE Workload Identity.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import gke, gce, crm, logs

GKE_METADATA_SERVER_CONTAINER_NAME = 'gke-metadata-server'
MATCH_STR = 'Unable to find pod: generic::not_found: retry budget exhausted'
MATCH_STR_END = 'not recorded in the snapshot'

# https://cloud.google.com/container-optimized-os/docs/how-to/logging
GCE_METADATA_COS_LOGGING_ENABLED = 'google-logging-enabled'
GCE_METADATA_COS_FLUENT_BIT = 'google-logging-use-fluentbit'
COS_LEGACY_AGENT_WARNING = 'Project metadata contains google-logging-enabled=true but not google-logging-use-fluentbit=true\nCOS VMs before Milestone 109 will use the deprecated legacy logging agent, which is not compatible with GKE Workload Identity. See https://cloud.google.com/container-optimized-os/docs/how-to/logging'

# k8s_container
metadata_server_errors = {}

def prepare_rule(context: models.Context):
  metadata_server_errors[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_container',
      log_name='log_id("stderr")',
      filter_str='severity=ERROR AND '+\
      f'resource.labels.container_name="{GKE_METADATA_SERVER_CONTAINER_NAME}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Check if GCP Project metadata is configured for legacy agent or fluent-bit
  project_metadata = gce.get_project_metadata(context.project_id)
  if project_metadata.get(GCE_METADATA_COS_LOGGING_ENABLED) == 'true' and \
    not project_metadata.get(GCE_METADATA_COS_FLUENT_BIT) == 'true':
    report.add_failed(crm.get_project(context.project_id), COS_LEGACY_AGENT_WARNING)

  # Search the logs.
  def filter_f(log_entry):
    try:
      if log_entry['jsonPayload']['message'].endswith(MATCH_STR_END) and MATCH_STR in log_entry['jsonPayload']['message']:
        return True
    except KeyError:
      return False

  clusters_with_errors = util.gke_logs_find_bad_clusters(
      context=context,
      logs_by_project=metadata_server_errors,
      filter_f=filter_f)

  for _, c in sorted(clusters.items()):
    if not c.has_workload_identity_enabled():
      report.add_skipped(c, 'GKE Workload Identity is disabled')
    elif c in clusters_with_errors:
      report.add_failed(c, logs.format_log_entry(clusters_with_errors[c]))
    else:
      report.add_ok(c)
