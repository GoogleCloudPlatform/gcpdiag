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
# Note that we don't have a general rule that checks this for all products,
# because the grant is done lazily, as soon as it is needed. So check that the
# grant is there only when resources of a certain product (like GKE clusters)
# are present, and we know that the grant is necessary for the correct
# operation of that product. Copy the rule for other products, as necessary.
"""
Data Fusion instance firewall rules are configured.

Private Data Fusion instances and Data Fusion versions below 6.2.0
require a firewall rule allowing incoming connections on TCP port 22
from the Data Fusion service to Dataproc VMs in the configured network.
"""
import ipaddress

from gcpdiag import lint, models
from gcpdiag.queries import datafusion
from gcpdiag.queries.datafusion import Version


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = datafusion.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')

  for instance in instances.values():

    if instance.is_private:
      # Private INGRESS i.network (Dataproc) <-- i.tp_ipv4_cidr:22 (Data Fusion TP)
      result = instance.network.firewall.check_connectivity_ingress(
          src_ip=instance.tp_ipv4_cidr, ip_protocol='tcp', port=22)

      if result.action == 'deny':
        if result.matched_by_str is None:
          report.add_failed(
              instance,
              'network %s is missing firewall rule allowing connections from %s over port %s.'
              % (instance.network.short_path, instance.tp_ipv4_cidr, 22))
        else:
          report.add_failed(
              instance,
              'connections from %s over port %s blocked by %s in network %s' %
              (instance.tp_ipv4_cidr, 22, result.matched_by_str,
               instance.network.short_path))

        continue

    elif instance.version < Version('6.2.0'):
      # Public INGRESS i.network (Dataproc) <-- 0.0.0.0/0:22 (Data Fusion TP)
      result = instance.network.firewall.check_connectivity_ingress(
          src_ip=ipaddress.ip_network('0.0.0.0/0'), ip_protocol='tcp', port=22)

      if result.action == 'deny':
        if result.matched_by_str is None:
          report.add_failed(
              instance,
              'network %s is missing firewall rule allowing connections from 0.0.0.0/0 over port %s'
              % (instance.network.short_path, 22))
        else:
          report.add_failed(
              instance,
              'connections from 0.0.0.0/0 over port %s blocked by %s in network %s'
              % (22, result.matched_by_str, instance.network.short_path))

        continue

    report.add_ok(instance)
