# Copyright 2022 Google LLC
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
"""Dataproc on GCE master VM is able to communicate with atleast one worker VM

The Compute Engine Virtual Machine instances (VMs) in a Dataproc cluster
must be able to communicate with each other using ICMP, TCP (all ports),
and UDP (all ports) protocols.
"""
import random

from gcpdiag import lint, models
from gcpdiag.queries import dataproc, gce

cluster_details = []


def prefetch_rule(context: models.Context):
  clusters = dataproc.get_clusters(context)
  for cluster in clusters:
    # Skip clusters in error state
    if cluster.status != 'ERROR':
      cluster_details.append({
          'cluster': cluster,
          'skipped': True,
          'reason': 'Cluster not in error state'
      })
      continue

    # Skip DPGKE clusters
    if not cluster.is_gce_cluster:
      cluster_details.append({
          'cluster': cluster,
          'skipped': True,
          'reason': 'Dataproc on GKE cluster'
      })
      continue

    # Skip single node clusters
    if cluster.is_single_node_cluster:
      cluster_details.append({
          'cluster': cluster,
          'skipped': True,
          'reason': 'Single node cluster'
      })
      continue

    # target
    target = gce.get_instance(project_id=context.project_id,
                              zone=cluster.zone,
                              instance_name=f'{cluster.name}-m')
    nic = None

    # get nic for network on target
    for interface in target.get_network_interfaces:
      if interface.get('network') == cluster.gce_network_uri:
        nic = interface.get('name')

    if nic:
      effective_firewalls = gce.get_instance_interface_effective_firewalls(
          target, nic)
    else:
      # log error
      continue

    # source
    source = gce.get_instance(project_id=context.project_id,
                              zone=cluster.zone,
                              instance_name=f'{cluster.name}-w-1')

    cluster_details.append({
        'cluster':
            cluster,
        'firewalls':
            effective_firewalls,
        'source_ip':
            source.get_network_ip_for_instance_interface(cluster.gce_network_uri
                                                        ),
        'source_sa':
            source.service_account,
        'source_tags':
            source.tags,
    })


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:

  # pylint: disable=unused-argument
  for detail in cluster_details:
    cluster = detail['cluster']

    if detail.get('skipped'):
      report.add_skipped(cluster, detail['reason'])
      continue

    firewalls = detail['firewalls']
    source_ip = detail['source_ip']
    source_sa = detail['source_sa']
    source_tags = detail['source_tags']

    # check ICMP
    icmp = firewalls.check_connectivity_ingress(
        src_ip=source_ip,
        ip_protocol='ICMP',
        source_service_account=source_sa,
        source_tags=source_tags)
    if icmp.action == 'deny':
      report.add_failed(
          cluster,
          f'ICMP connections must be allowed, blocked by: {icmp.matched_by_str}'
      )
      continue

    port = random.randint(0, 65535)

    # check random TCP port
    tcp = firewalls.check_connectivity_ingress(src_ip=source_ip,
                                               ip_protocol='TCP',
                                               port=port,
                                               source_service_account=source_sa,
                                               source_tags=source_tags)
    if tcp.action == 'deny':
      report.add_failed(
          cluster,
          f'TCP connections must be allowed on all ports, blocked by: {tcp.matched_by_str}'
      )
      continue

    # check random udp port
    udp = firewalls.check_connectivity_ingress(src_ip=source_ip,
                                               ip_protocol='UDP',
                                               port=port,
                                               source_service_account=source_sa,
                                               source_tags=source_tags)
    if udp.action == 'deny':
      report.add_failed(
          cluster,
          f'UDP connections must be allowed on all ports, blocked by: {udp.matched_by_str}'
      )
      continue

    report.add_ok(cluster)
