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
"""Per-project quotas are not near the limit.

A project level quota restricts how much of a particular shared Google Cloud
resource you can use in a given Cloud project, including hardware, software,
and network components.

Rule will start failing if any project level quota usage is higher than 80%.
"""

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import crm, gce, monitoring, quotas

GCE_SERVICE_NAME = 'compute.googleapis.com'
# name of the quota limit : name of the quota metric
QUOTA_LIST = {
    'BACKEND-BUCKETS-per-project':
        'compute.googleapis.com/backend_buckets',
    'BACKEND-SERVICES-per-project':
        'compute.googleapis.com/backend_services',
    'FIREWALLS-per-project':
        'compute.googleapis.com/firewalls',
    'FORWARDING-RULES-per-project':
        'compute.googleapis.com/forwarding_rules',
    'GLOBAL-EXTERNAL-MANAGED-FORWARDING-RULES-per-project':
        'compute.googleapis.com/global_external_managed_forwarding_rules',
    'INTERNAL-TRAFFIC-DIRECTOR-FORWARDING-RULES-per-project':
        'compute.googleapis.com/internal_traffic_director_forwarding_rules',
    'GLOBAL-INTERNAL-ADDRESSES-per-project':
        'compute.googleapis.com/global_internal_addresses',
    'HEALTH-CHECK-SERVICES-per-project':
        'compute.googleapis.com/health_check_services',
    'HEALTH-CHECKS-per-project':
        'compute.googleapis.com/health_checks',
    'IMAGES-per-project':
        'compute.googleapis.com/images',
    'MACHINE-IMAGES-per-project':
        'compute.googleapis.com/machine_images',
    'INSTANCE-TEMPLATES-per-project':
        'compute.googleapis.com/instance_templates',
    'INTERCONNECTS-per-project':
        'compute.googleapis.com/interconnects',
    'INTERCONNECT-TOTAL-GBPS-per-project':
        'compute.googleapis.com/interconnect_total_gbps',
    'IN-USE-ADDRESSES-per-project':
        'compute.googleapis.com/global_in_use_addresses',
    'NETWORKS-per-project':
        'compute.googleapis.com/networks',
    'NETWORK-FIREWALL-POLICIES-per-project':
        'compute.googleapis.com/network_firewall_policies',
    'NETWORK-ENDPOINT-GROUPS-per-project':
        'compute.googleapis.com/global_network_endpoint_groups',
    'NOTIFICATION-ENDPOINTS-per-project':
        'compute.googleapis.com/notification_endpoints',
    'PUBLIC-ADVERTISED-PREFIXES-per-project':
        'compute.googleapis.com/public_advertised_prefixes',
    'PUBLIC-DELEGATED-PREFIXES-per-project':
        'compute.googleapis.com/global_public_delegated_prefixes',
    'ROUTERS-per-project':
        'compute.googleapis.com/routers',
    'ROUTES-per-project':
        'compute.googleapis.com/routes',
    'PACKET-MIRRORINGS-per-project':
        'compute.googleapis.com/packet_mirrorings',
    'SECURITY-POLICIES-per-project':
        'compute.googleapis.com/security_policies',
    'SECURITY-POLICY-CEVAL-RULES-per-project':
        'compute.googleapis.com/security_policy_ceval_rules',
    'SECURITY-POLICY-RULES-per-project':
        'compute.googleapis.com/security_policy_rules',
    'SNAPSHOTS-per-project':
        'compute.googleapis.com/snapshots',
    'SSL-CERTIFICATES-per-project':
        'compute.googleapis.com/ssl_certificates',
    'SSL-POLICIES-per-project':
        'compute.googleapis.com/ssl_policies',
    'STATIC-ADDRESSES-per-project':
        'compute.googleapis.com/global_static_addresses',
    'STATIC-BYOIP-ADDRESSES-per-project':
        'compute.googleapis.com/global_static_byoip_addresses',
    'EXTERNAL-IPV6-SPACES-per-project':
        'compute.googleapis.com/global_external_ipv6_spaces',
    'SUBNETWORKS-per-project':
        'compute.googleapis.com/subnetworks',
    'PRIVATE-V6-ACCESS-SUBNETWORKS-per-project':
        'compute.googleapis.com/private_v6_access_subnetworks',
    'SUBNETWORK-RANGES-UNDER-ALL-AGGREGATES-per-project':
        'compute.googleapis.com/subnetwork_ranges_under_all_aggregates',
    'TARGET-GRPC-PROXIES-per-project':
        'compute.googleapis.com/target_grpc_proxies',
    'TARGET-HTTP-PROXIES-per-project':
        'compute.googleapis.com/target_http_proxies',
    'TARGET-HTTPS-PROXIES-per-project':
        'compute.googleapis.com/target_https_proxies',
    'TARGET-INSTANCES-per-project':
        'compute.googleapis.com/target_instances',
    'TARGET-POOLS-per-project':
        'compute.googleapis.com/target_pools',
    'TARGET-SSL-PROXIES-per-project':
        'compute.googleapis.com/target_ssl_proxies',
    'TARGET-TCP-PROXIES-per-project':
        'compute.googleapis.com/target_tcp_proxies',
    'TARGET-VPN-GATEWAYS-per-project':
        'compute.googleapis.com/target_vpn_gateways',
    'CPUS-ALL-REGIONS-per-project':
        'compute.googleapis.com/cpus_all_regions',
    'GPUS-ALL-REGIONS-per-project':
        'compute.googleapis.com/gpus_all_regions',
    'URL-MAPS-per-project':
        'compute.googleapis.com/url_maps',
    'VPN-GATEWAYS-per-project':
        'compute.googleapis.com/vpn_gateways',
    'EXTERNAL-VPN-GATEWAYS-per-project':
        'compute.googleapis.com/external_vpn_gateways',
    'VPN-TUNNELS-per-project':
        'compute.googleapis.com/vpn_tunnels',
    'XPN-SERVICE-PROJECTS-per-project':
        'compute.googleapis.com/xpn_service_projects'
}
# percentage of the quota limit usage
QUOTA_LIMIT_THRESHOLD = 0.80
_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):
  quota_limit_names = '|'.join(QUOTA_LIST.keys())
  params = {
      'service_name': GCE_SERVICE_NAME,
      'limit_name': quota_limit_names,
      'within_days': config.get('within_days')
  }
  _query_results_per_project_id[context.project_id] = \
      monitoring.query(
          context.project_id,
          quotas.CONSUMER_QUOTA_QUERY_TEMPLATE.format_map(params))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  region = gce.Region(context.project_id, {'name': 'global', 'selfLink': ''})
  #set region to global as this is project level quota

  if len(_query_results_per_project_id[context.project_id]) == 0:
    report.add_skipped(project, 'no data')
    return

  all_skipped = True
  for quota_metrics_name in QUOTA_LIST.values():
    ts_key = frozenset({
        f'resource.project_id:{context.project_id}',
        f'metric.quota_metric:{quota_metrics_name}',
        f'resource.location:{region.name}'
    })
    try:
      ts = _query_results_per_project_id[context.project_id][ts_key]
      all_skipped = False
    except KeyError:
      # silently skip
      continue

    # did we exceeded threshold on any day?
    exceeded = False
    for day_value in ts['values']:
      ratio = day_value[0]
      limit = day_value[1]
      if ratio > QUOTA_LIMIT_THRESHOLD:
        exceeded = True
        break

    if exceeded:
      report.add_failed(project,
                        (f'Project has reached {ratio:.0%} of {limit} limit:\n'
                         f' quota metric: {quota_metrics_name}'))
    else:
      report.add_ok(project, f' quota metric: {quota_metrics_name}')

  # report skip if all data for region not available
  if all_skipped:
    report.add_skipped(project, 'no data')
