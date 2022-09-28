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
Private Data Fusion instance is peered to the tenant project.

Private Data Fusion instance requires peered connection to
Data Fusion tenant project.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import datafusion


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = datafusion.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')

  for instance in instances.values():

    if instance.is_private:

      is_peered_to_tp = False

      if instance.network.peerings is not None:

        #Check all peered connections for the correct Data Fusion one.
        for peer in instance.network.peerings:
          match = re.match(
              r'https://www.googleapis.com/compute/([^/]+)/'
              'projects/([^/]+)/([^/]+)/networks/([^/]+)$', peer.url)

          if match:
            peered_project = match.group(2)
            peered_network = match.group(4)

            if peered_project == instance.tenant_project_id:
              if instance.location in peered_network:

                #Data Fusion peered VPC network name = INSTANCE_REGION-INSTANCE_ID
                peer_instance_name = peered_network.removeprefix(
                    instance.location)
                peer_instance_name = peer_instance_name.removeprefix('-')

                if peer_instance_name == instance.name:
                  if peer.state == 'ACTIVE':
                    if peer.exports_custom_routes:
                      if peer.imports_custom_routes:

                        is_peered_to_tp = True
                        break

                      else:
                        report.add_failed(
                            instance,
                            (f'peered connection {peer.name} in network '
                             f'{instance.network.short_path} '
                             f'is not importing custom routes.'))

                    else:
                      report.add_failed(
                          instance,
                          (f'peered connection {peer.name} in network '
                           f'{instance.network.short_path} '
                           f'is not exporting custom routes.'))

                  else:
                    report.add_failed(
                        instance,
                        (f'peered connection {peer.name} in network '
                         f'{instance.network.short_path} is not active.'))

          else:
            report.add_failed(
                instance,
                (f'failed to extract project id and network id from peer url '
                 f'{peer.url}.'))

      if not is_peered_to_tp:
        report.add_failed(
            instance,
            (f'private instance network {instance.network.short_path} '
             f'is not correctly peered to tenant project '
             f'{instance.tenant_project_id}.'))
      else:
        report.add_ok(instance)

    else:
      report.add_ok(instance)
