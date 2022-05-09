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
"""Cloud SQL is not using Docker bridge network.

The IP range 172.17.0.0/16 is reserved for the Docker bridge network.
Any Cloud SQL instances created with an IP in that range will be unreachable.
Connections from any IP within that range to Cloud SQL instances using private
IP fail.
"""

import ipaddress

from gcpdiag import lint, models
from gcpdiag.queries import apis, cloudsql

DOCKER_BRIDGE_NETWORK = ipaddress.ip_network('172.17.0.0/16')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    report.add_skipped(None, 'sqladmin is disabled')
    return

  instances = cloudsql.get_instances(context)

  if not instances:
    report.add_skipped(None, 'no CloudSQL instances found')
    return

  for instance in instances:
    if any(_is_docker_bridge_ip(ip) for ip in instance.ip_addresses):
      report.add_failed(instance,
                        f'{instance.name} is inside of Docker bridge network')
    else:
      report.add_ok(instance)


def _is_docker_bridge_ip(ip: ipaddress.IPv4Address) -> bool:
  return ip in DOCKER_BRIDGE_NETWORK
