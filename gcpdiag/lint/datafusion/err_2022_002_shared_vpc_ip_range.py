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
Private Data Fusion instance has valid host VPC IP range.

Private Data Fusion instance using Shared VPC requires
'Service Networking API' to be enabled, and an IP range of at least /22.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, datafusion


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = datafusion.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')

  for instance in instances.values():
    if instance.is_private and instance.uses_shared_vpc:
      match = re.match(r'([^/]+)/([^/]+)$', instance.network.short_path)
      if match:
        host_project = match.group(1)
        if apis.is_enabled(host_project, 'servicenetworking'):
          if instance.tp_ipv4_cidr is not None:
            if instance.tp_ipv4_cidr.prefixlen > 22:
              report.add_failed(
                  instance,
                  'Allocated IP range %s in host VPC network %s is too small.' %
                  (instance.tp_ipv4_cidr, instance.network.short_path))
          else:
            report.add_failed(
                instance,
                'Host VPC network %s has no Data Fusion allocated IP range.' %
                (instance.network.short_path))

        else:
          report.add_failed(
              instance,
              'Service Networking API disabled in host VPC project %s.' %
              (host_project))
      else:
        report.add_failed(
            instance, 'failed to extract project id from network path %s.' %
            (instance.network.short_path))

    report.add_ok(instance)
