# Lint as: python3
"""Stateful workloads not run on preemptible node

Stateful workloads run on preemptible node are likely to be more frequently
disrupted by node termination with a short grace period. Please fully test
before you decide to run stateful workloads on preemptible node to avoid app
level service interruption or data corruption. Visit site below for more info:
https://cloud.google.com/kubernetes-engine/docs/concepts/spot-vms#best-practices
"""

from gcpdiag import lint, models
from gcpdiag.queries import gce, gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  instances = gce.get_instances(context=context)
  clusters = gke.get_clusters(context=context)

  # A 'failed cluster' in this rule is defined as a GKE cluster that:
  # 1. has at least one preemptible node
  # 2. the preemptible node has at least one writeable non-boot PD attached
  failed_clusters = set()
  for i in instances.values():
    if i.is_gke_node() and i.is_preemptible_vm():
      for d in i.disks:
        # Skip checking if the disk is not PD (e.g. localSSD)
        if 'type' in d and d['type'] != 'PERSISTENT':
          continue
        # Skip checking if the PD is not writeable
        if 'mode' in d and 'WRITE' not in d['mode']:
          continue
        # A writeable non-boot PD indicates stateful workloads on this node.
        if 'boot' in d and not d['boot']:
          instance_cluster_name = i.get_metadata('cluster-name')
          instance_zone = i.zone
          for c in clusters.values():
            if instance_cluster_name == c.name and c.location in instance_zone:
              failed_clusters.add(c)

  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for c in sorted(clusters.values(), key=lambda cluster: cluster.short_path):
    if c not in failed_clusters:
      report.add_ok(c)
    else:
      report.add_failed(c, (
          f'Stateful workload is running on preemptible/spot node(s) "{c.name}"'
      ))
