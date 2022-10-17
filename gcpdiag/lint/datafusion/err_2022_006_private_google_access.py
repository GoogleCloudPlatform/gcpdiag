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
Private Google Access enabled for private Data Fusion instance subnetwork.

Private Google Access required on private Data Fusion instance subnetwork.
"""

from gcpdiag import lint, models
from gcpdiag.queries import datafusion


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = datafusion.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')

  for instance in instances.values():

    if instance.is_private:

      is_private_ip_google_access = False

      for subnet in instance.network.subnetworks.values():
        if subnet.region == instance.location:
          is_private_ip_google_access = subnet.is_private_ip_google_access()
          if is_private_ip_google_access:
            break

      if not is_private_ip_google_access:
        report.add_failed(instance,
                          (f'Private Google Access is not enabled on '
                           f'subnetwork with region {instance.location} '
                           f'in network {instance.network.short_path}'))
      else:
        report.add_ok(instance)

    else:
      report.add_ok(instance)
