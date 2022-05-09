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
"""Cloud SQL Docker bridge network should be avoided.

The IP range 172.17.0.0/16 is reserved for the Docker bridge network.
Connections from any IP within that range to Cloud SQL instances using private
IP fail.
"""

import ipaddress
import operator as op
import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, gce, network

DOCKER_BRIDGE_NETWORK = ipaddress.ip_network('172.17.0.0/16')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'compute'):
    report.add_skipped(None, 'computer is disabled')
    return

  instances = gce.get_instances(context)

  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  cloudsql_peered_networks = {}

  for vpc in network.get_networks(context.project_id):
    if any(_is_cloudsql_peer_network(peer.url) for peer in vpc.peerings):
      cloudsql_peered_networks[vpc.self_link] = vpc

  if not cloudsql_peered_networks:
    report.add_skipped(None, 'no Cloud SQL peered vpc found')
    return

  for instance in sorted(instances.values(),
                         key=op.attrgetter('project_id', 'name')):
    if not any(network.self_link in cloudsql_peered_networks
               for network in instance.networks):
      report.add_skipped(instance, 'not in the Cloud SQL peered vpc')
      continue

    if any(_is_docker_bridge_ip(ip) for ip in instance.network_ips):
      report.add_failed(instance,
                        f'{instance.name} is inside of Docker bridge network')
    else:
      report.add_ok(instance)


def _is_cloudsql_peer_network(url: str) -> bool:
  pattern = 'https://www.googleapis.com/compute/v1/projects/speckle-umbrella.*/cloud-sql-network-.*'
  return re.match(pattern, url) is not None


def _is_docker_bridge_ip(ip: ipaddress.IPv4Address) -> bool:
  return ip in DOCKER_BRIDGE_NETWORK
