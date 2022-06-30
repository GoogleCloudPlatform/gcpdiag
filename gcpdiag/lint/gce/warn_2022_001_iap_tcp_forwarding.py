#
# Copyright 2022 Google LLC
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
"""GCE connectivity: IAP service can connect to SSH/RDP port on instances.

Traffic from the IP range 35.235.240.0/20 to VM instances is necessary for
IAP TCP forwarding to establish an encrypted tunnel over which you can forward
SSH, RDP traffic to VM instances.
"""
import ipaddress

from gcpdiag import lint, models
from gcpdiag.queries import gce

VERIFY_PORTS = {  #
    'ssh': 22,
    'rdp': 3389
}

IAP_SOURCE_NETWORK = ipaddress.ip_network('35.235.240.0/20')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
  else:
    for instance in sorted(instances, key=lambda i: i.name):
      network = instance.network
      port = VERIFY_PORTS['ssh']
      if instance.is_windows_machine():
        port = VERIFY_PORTS['rdp']
      result = network.firewall.check_connectivity_ingress(
          src_ip=IAP_SOURCE_NETWORK,
          ip_protocol='tcp',
          port=port,
          target_service_account=instance.service_account,
          target_tags=instance.tags)
      if result.action == 'deny':
        report.add_failed(
            instance,
            (f'connections from {IAP_SOURCE_NETWORK} to tcp:{port} blocked by '
             f'{result.matched_by_str} (instance: {instance.name})'))
      else:
        report.add_ok(instance)
