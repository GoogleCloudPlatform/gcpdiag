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

# Lint as: python3
"""PAYG licensed Windows instance can reach KMS to activate

Validate if a Microsoft Windows instance is able to activate using GCP PAYG license.
"""
import ipaddress
import operator as op

from gcpdiag import lint, models, utils
from gcpdiag.queries import gce

KMS_FW_RULE = ipaddress.ip_network('35.190.247.13/32')
KMS_PORT = 1688
DEFAULT_FW_RULE = ipaddress.ip_network('0.0.0.0/0')
NEXT_HOP = 'default-internet-gateway'
KMS_ROUTE = ipaddress.ip_network('35.190.247.13/32')


# verify KMS is accessible for a given route
def kms_route_access(instance) -> bool:
  for route in instance.routes:
    if route.next_hop_gateway == (
        f'https://www.googleapis.com/compute/v1/projects/'
        f'{route.project_id}/global/gateways/{NEXT_HOP}'
    ) and route.check_route_match(KMS_ROUTE, route.dest_range):
      return True
  return False


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  # skip entire rule if no instances
  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
    return

  # Load gcp non-byol licenses
  licenses = gce.get_gce_public_licences('windows-cloud')
  payg_licenses = [x for x in licenses if not x.endswith('-byol')]

  # Add windows to new list and skip entire rule if no Windows instances
  for instance in sorted(instances, key=op.attrgetter('project_id', 'name')):
    fault_list = []
    is_faulty = False
    # Skip non-Windows machines
    if not instance.is_windows_machine():
      continue
    # Skip BYOL instances
    if not instance.check_license(payg_licenses):
      report.add_skipped(instance, 'No PAYG licence attached to this instance')
      continue
    # Check for public IP instances
    if instance.is_public_machine():
      # Firewall rule check
      result = instance.network.firewall.check_connectivity_egress(
          src_ip=KMS_FW_RULE,
          ip_protocol='tcp',
          port=KMS_PORT,
          target_service_account=instance.service_account,
          target_tags=instance.tags)
      if result.action == 'deny':
        # Implied deny is a pass for external IP instances
        if result.matched_by_str is not None:
          fault_list.append(
              f'connections from {KMS_FW_RULE} to tcp:{KMS_PORT} blocked by '
              f'{result.matched_by_str}')
          is_faulty = True
    # Check for private IP instances
    else:
      # PGA check
      for subnetwork in instance.subnetworks:
        if not subnetwork.is_private_ip_google_access():
          fault_list.append(
              f'Subnetwork {subnetwork.name} does not have Private Google Access enabled.'
          )
          is_faulty = True
      # Firewall rule check
      result = instance.network.firewall.check_connectivity_egress(
          src_ip=KMS_FW_RULE,
          ip_protocol='tcp',
          port=KMS_PORT,
          target_service_account=instance.service_account,
          target_tags=instance.tags)
      if result.action == 'deny':
        if result.matched_by_str is None:
          fault_list.append(
              f'Connectivity to {KMS_FW_RULE} and port tcp:{KMS_PORT} not found '
              f'in VPC.')
        else:
          fault_list.append(
              f'connections from {KMS_FW_RULE} to tcp:{KMS_PORT} blocked by '
              f'{result.matched_by_str}.')
        is_faulty = True
    # Routes Check
    if not kms_route_access(instance):
      fault_list.append(
          f'Route {KMS_ROUTE} with next hop {NEXT_HOP} not found in VPC.')
      is_faulty = True
    if is_faulty:
      report.add_failed(instance, utils.format_fault_list(fault_list))
    else:
      report.add_ok(instance)
