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
"""GKE Node Auto Provisioning scales nodes to match workload demands.

If a GKE cluster has Node Auto Provisioning (NAP) enabled, resource limits
are configured to support workload scaling. Increased demand triggers
successful node creation, ensuring application continuity.

If NAP resource limits (CPU, memory) are configured too low, the autoscaler
may be unable to add new nodes during high demand. This could potentially
cause application disruptions.  To prevent this, ensure NAP resource limits
are set appropriately or consider manually scaling node pools as needed.
"""

from typing import Optional, Tuple

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

_LOG_RESOURCE_TYPE = 'k8s_cluster'
_LOG_NAME = (
    'log_id("container.googleapis.com%2Fcluster-autoscaler-visibility")')
_LOG_FILTER_STR = (
    'jsonPayload.noDecisionStatus.noScaleUp.unhandledPodGroups.'
    'napFailureReasons.messageId="no.scale.up.nap.pod.zonal.resources.exceeded"'
)

MATCH_STR_1 = 'no.scale.up.nap.pod.zonal.resources.exceeded'
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


def _filter_f(log_entry: logs.LogEntryShort) -> bool:
  try:
    return MATCH_STR_1 in get_path(
        log_entry,
        (
            'jsonPayload',
            'noDecisionStatus',
            'noScaleUp',
            'unhandledPodGroups',
            0,
            'napFailureReasons',
            0,
            'messageId',
        ),
    )
  except KeyError:
    return False


def _extract_sample_affected_pod(
    log_entry: logs.LogEntryShort,) -> Tuple[Optional[str], Optional[str]]:
  try:
    pod_group = get_path(
        log_entry,
        (
            'jsonPayload',
            'noDecisionStatus',
            'noScaleUp',
            'unhandledPodGroups',
            0,
            'podGroup',
            'samplePod',
        ),
    )
    return (pod_group['namespace'], pod_group['name'])
  except KeyError:
    return (None, None)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule if logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Search the logs.
  bad_clusters = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=logs_by_project, filter_f=_filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_clusters:
      namespace, name = _extract_sample_affected_pod(bad_clusters[c])
      message = (
          'NAP cannot scale-up since cluster-wide cpu and/or memory limits'
          ' would be exceeded.')
      if namespace and name:
        message += f' Sample affected pod: {namespace}/{name}.'
      report.add_failed(c, message)
    else:
      report.add_ok(c)
