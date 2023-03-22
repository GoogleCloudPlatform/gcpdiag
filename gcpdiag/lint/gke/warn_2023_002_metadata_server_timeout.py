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
"""GKE workload timeout to Compute Engine metadata server.

If the workload uses a Google Authentication library, the default timeout
for requests to the Compute Engine Metadata server might be too aggressive.

Failed requests may return something like 'DefaultCredentialsError'.
"""

from collections import defaultdict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, gke, logs

CREDENTIALS_ERROR_LOG_FILTER = [
    'severity=ERROR',
    ('textPayload: "google.auth.exceptions.DefaultCredentialsError: '
     'Your default credentials were not found."')
]
credential_logs_by_project = {}


def prepare_rule(context: models.Context):

  credential_logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_container',
      log_name='log_id("stderr")',
      filter_str=' AND '.join(CREDENTIALS_ERROR_LOG_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  # Skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  clusters = gke.get_clusters(context)

  # Skip if no clusters found
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Clusters/containers with error from logs
  error_clusters: dict[tuple[str, str], set] = defaultdict(set)

  for log_entry in credential_logs_by_project[context.project_id].entries:
    cluster_name = get_path(log_entry, ('resource', 'labels', 'cluster_name'))
    location = get_path(log_entry, ('resource', 'labels', 'location'))
    container_name = get_path(log_entry,
                              ('resource', 'labels', 'container_name'))

    # Add container name to report failure
    if container_name:
      error_clusters[cluster_name, location].add(container_name)

  # Report final results
  for _, c in sorted(clusters.items()):
    if (c.name, c.location) in error_clusters:
      report.add_failed(
          c, 'Failed containers: %s' %
          ', '.join(error_clusters[(c.name, c.location)]))
    else:
      report.add_ok(c)
