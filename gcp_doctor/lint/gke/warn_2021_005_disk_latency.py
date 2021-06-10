# Lint as: python3
"""GKE nodes have good disk performance.

Disk performance is essential for the proper operation of GKE nodes. If
too much IO is done and the disk latency gets too high, system components
can start to misbehave. Often the boot disk is a bottleneck because it is
used for multiple things: the operating system, docker images, container
filesystems (usually including /tmp, etc.), and EmptyDir volumes.
"""

from typing import Any, Dict

from gcp_doctor import lint, models
from gcp_doctor.queries import gce, gke, monitoring

# TODO(dwes): this should be configurable, maybe with a --within command-line
#             argument.
WITHIN_DAYS = 3
SLO_LATENCY_MS = 100
# SLO: at least 99.5% of minutes are good (7 minutes in a day)
SLO_BAD_MINUTES_RATIO = 0.005
# If we have less than this minutes measured, skip
SLO_VALID_MINUTES_PER_DAY = 12 * 60

_prefetched_query_results: monitoring.TimeSeriesCollection


def prefetch_rule(context: models.Context):
  # Fetch the metrics for all nodes.
  #
  # Note: we only group_by instance_id because of performance reasons (it gets
  # much slower if you group_by multiple labels)
  clusters = gke.get_clusters(context)
  if not clusters:
    return

  within_str = 'within %dd, d\'%s\'' % (WITHIN_DAYS,
                                        monitoring.period_aligned_now(60))
  global _prefetched_query_results
  _prefetched_query_results = monitoring.query(
      context, f"""
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

  # Create a mapping from instance id to cluster so that we can link back the
  # instance metrics to the clusters.
  instance_id_to_cluster_id = dict()
  instance_id_to_instance_name = dict()
  for instance_id, instance in gce.get_instances(context).items():
    try:
      cluster_project = instance.project_id
      cluster_name = instance.get_metadata('cluster-name')
      cluster_location = instance.get_metadata('cluster-location')
      # Unfortunately cluster-uid is not available in the cluster description
      cluster_id = (cluster_project, cluster_location, cluster_name)
      instance_id_to_cluster_id[instance_id] = cluster_id
      instance_id_to_instance_name[instance_id] = instance.name
    except KeyError:
      continue

  # Map "cluster_ids" (see above) to cluster objects
  cluster_id_to_cluster = dict()
  for c in clusters.values():
    cluster_id = (c.project_id, c.location, c.name)
    cluster_id_to_cluster[cluster_id] = c

  # Organize data per-cluster.
  per_cluster_results: Dict[gke.Cluster, Dict[str, Any]] = dict()
  global _prefetched_query_results
  for ts in _prefetched_query_results.values():
    instance_id = ts['labels']['resource.instance_id']
    try:
      cluster_id = instance_id_to_cluster_id[instance_id]
      cluster = cluster_id_to_cluster[cluster_id]
      instance_name = instance_id_to_instance_name[instance_id]
    except KeyError:
      continue
    cluster_results = per_cluster_results.setdefault(cluster, {
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
          (instance_name, total_minutes, total_minutes_bad))

  # Go over all selected clusters and report results.
  for _, c in sorted(clusters.items()):
    if c not in per_cluster_results or not per_cluster_results[c]['valid']:
      report.add_skipped(c, 'no data')
    elif not per_cluster_results[c]['bad_instances']:
      report.add_ok(c)
    else:
      report.add_failed(
          c,
          f'disk latency >{SLO_LATENCY_MS}ms (1 min. avg., within {WITHIN_DAYS} days): \n. '
          + '\n. '.join([
              f'{i[0]} ({i[2]} out of {i[1]} minutes bad)'
              for i in sorted(per_cluster_results[c]['bad_instances'])
          ]))
