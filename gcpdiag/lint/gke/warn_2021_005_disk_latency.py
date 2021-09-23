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

# Lint as: python3
"""GKE nodes have good disk performance.

Disk performance is essential for the proper operation of GKE nodes. If
too much IO is done and the disk latency gets too high, system components
can start to misbehave. Often the boot disk is a bottleneck because it is
used for multiple things: the operating system, docker images, container
filesystems (usually including /tmp, etc.), and EmptyDir volumes.
"""

from typing import Any, Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import gke, monitoring

SLO_LATENCY_MS = 100
# SLO: at least 99.5% of minutes are good (7 minutes in a day)
SLO_BAD_MINUTES_RATIO = 0.005
# If we have less than this minutes measured, skip
SLO_VALID_MINUTES_PER_DAY = 12 * 60

_query_results_per_project_id: Dict[str,
                                    monitoring.TimeSeriesCollection] = dict()


def prefetch_rule(context: models.Context):
  # Fetch the metrics for all nodes.
  #
  # Note: we only group_by instance_id because of performance reasons (it gets
  # much slower if you group_by multiple labels)
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  within_str = 'within %dd, d\'%s\'' % (config.WITHIN_DAYS,
                                        monitoring.period_aligned_now(60))
  global _query_results_per_project_id
  _query_results_per_project_id[context.project_id] = monitoring.query(
      context.project_id, f"""
fetch gce_instance
  | {{ metric 'compute.googleapis.com/guest/disk/operation_time' ;
      metric 'compute.googleapis.com/guest/disk/operation_count' }}
  | {within_str}
  | filter metric.device_name = 'sda'
  | group_by [resource.instance_id], .sum()
  | every 1m
  | ratio
  | value(val() > cast_units({SLO_LATENCY_MS}, "ms"))
  | group_by 1d, [ .count_true, .count ]
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Organize data per-cluster.
  per_cluster_results: Dict[gke.Cluster, Dict[str, Any]] = dict()
  global _query_results_per_project_id
  for ts in _query_results_per_project_id[context.project_id].values():
    instance_id = ts['labels']['resource.instance_id']
    try:
      node = gke.get_node_by_instance_id(context, instance_id)
    except KeyError:
      continue
    cluster_results = per_cluster_results.setdefault(node.nodepool.cluster, {
        'bad_instances': [],
        'valid': False
    })
    # Did we miss the SLO on any day?
    # note: we don't calculate the SLO for the whole "WITHIN_DAYS" period
    # because otherwise you would get different results depending on how that
    # period is defined.
    total_minutes_bad = 0
    total_minutes = 0
    slo_missed = 0
    for day_value in ts['values']:
      total_minutes_bad += day_value[0]
      total_minutes += day_value[1]
      if day_value[1] > SLO_VALID_MINUTES_PER_DAY:
        cluster_results['valid'] = 1
        if day_value[0] / day_value[1] > SLO_BAD_MINUTES_RATIO:
          slo_missed = 1

    if slo_missed:
      cluster_results['bad_instances'].append(
          (node.instance.name, total_minutes, total_minutes_bad))

  # Go over all selected clusters and report results.
  for _, c in sorted(clusters.items()):
    if c not in per_cluster_results or not per_cluster_results[c]['valid']:
      report.add_skipped(c, 'no data')
    elif not per_cluster_results[c]['bad_instances']:
      report.add_ok(c)
    else:
      report.add_failed(
          c,
          f'disk latency >{SLO_LATENCY_MS}ms (1 min. avg., within {config.WITHIN_DAYS} days): \n. '
          + '\n. '.join([
              f'{i[0]} ({i[2]} out of {i[1]} minutes bad)'
              for i in sorted(per_cluster_results[c]['bad_instances'])
          ]))
