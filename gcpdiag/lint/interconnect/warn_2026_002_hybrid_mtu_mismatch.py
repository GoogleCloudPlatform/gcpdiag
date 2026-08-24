# Lint as: python3
"""Detect potential packet loss due to MTU mismatches in hybrid connectivity.

This rule checks for two conditions:
1.  Evidence of packet drops due to exceeding MTU on Cloud Interconnect
    attachments or Cloud VPN gateways, by querying Cloud Monitoring metrics.
2.  Mismatched MTU settings between Cloud Interconnect VLAN attachments and
    their associated VPC networks.

Mismatched MTUs can lead to silent packet drops, especially for UDP traffic or
when Path MTU Discovery (PMTUD) is not functioning end-to-end. This often
occurs in hybrid setups with asymmetric routing.
"""

import logging
from typing import Any, Dict, Optional, Set, Tuple

from gcpdiag import lint, models
from gcpdiag.queries import crm, interconnect, monitoring, network


class PathOnlyResource(models.Resource):
  """A dummy resource class that only wraps a resource path."""

  def __init__(self, project_id: str, full_path: str):
    super().__init__(project_id=project_id)
    self._full_path = full_path

  @property
  def full_path(self) -> str:
    return self._full_path


# Module-level cache for query results
query_results_per_project_id: Dict[str, Dict[str, Any]] = {}


def get_interconnect_mql_query(metric_name: str, within_str: str, drop_reason: str) -> str:
  """Helper function to generate the MQL query for Interconnect."""
  return f"""
  fetch interconnect_attachment
  | metric '{metric_name}'
  | filter (metric.drop_reason == '{drop_reason}')
  | align rate(1m)
  | group_by [resource.attachment, resource.region],
      [value_dropped_aggregate: aggregate(value.{metric_name.split('/')[-1]})]
  | within {within_str}
  """


def get_vpn_mql_query(within_str: str) -> str:
  """Helper function to generate the MQL query for VPN MTU drops."""
  metric_name = 'vpn.googleapis.com/network/sent_packets_count'
  return f"""
  fetch vpn_gateway
  | metric '{metric_name}'
  | filter (metric.status == 'exceeds_mtu')
  | align rate(1m)
  | group_by [resource.gateway_id, resource.region],
      [value_dropped_aggregate: aggregate(value.sent_packets_count)]
  | within {within_str}
  """


def prefetch_rule(context: models.Context):
  """Prefetch monitoring data for MTU-related packet drops."""
  project_id = context.project_id
  if project_id in query_results_per_project_id:
    return

  within_str = '7d'
  query_results_per_project_id[project_id] = {}

  # Interconnect Egress Query
  egress_metric = 'interconnect.googleapis.com/network/attachment/egress_dropped_packets_count'
  mql_query_ic_egress = get_interconnect_mql_query(egress_metric, within_str, 'EXCEEDS_MTU')
  try:
    logging.debug(f'gcpdiag-rule-debug: Interconnect Egress MQL Query:\n{mql_query_ic_egress}')
    query_results_per_project_id[project_id]['ic_egress'] = monitoring.query(
      project_id, mql_query_ic_egress
    )
  except Exception as e:
    logging.warning(f'Failed to query Interconnect egress dropped packets for {project_id}: {e!r}')
    query_results_per_project_id[project_id]['ic_egress'] = e

  # Interconnect Ingress Query
  ingress_metric = 'interconnect.googleapis.com/network/attachment/ingress_dropped_packets_count'
  mql_query_ic_ingress = get_interconnect_mql_query(ingress_metric, within_str, 'EXCEEDS_MTU')
  try:
    logging.debug(f'gcpdiag-rule-debug: Interconnect Ingress MQL Query:\n{mql_query_ic_ingress}')
    query_results_per_project_id[project_id]['ic_ingress'] = monitoring.query(
      project_id, mql_query_ic_ingress
    )
  except Exception as e:
    logging.warning(f'Failed to query Interconnect ingress dropped packets for {project_id}: {e!r}')
    query_results_per_project_id[project_id]['ic_ingress'] = e

  # VPN Egress Query
  mql_query_vpn = get_vpn_mql_query(within_str)
  try:
    logging.debug(f'gcpdiag-rule-debug: VPN Egress MQL Query:\n{mql_query_vpn}')
    query_results_per_project_id[project_id]['vpn_egress'] = monitoring.query(
      project_id, mql_query_vpn
    )
  except Exception as e:
    logging.warning(f'Failed to query VPN egress dropped packets for {project_id}: {e!r}')
    query_results_per_project_id[project_id]['vpn_egress'] = e


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project_id = context.project_id
  project_resource = crm.get_project(project_id)
  logging.debug(f'gcpdiag-rule-debug: Running MTU mismatch rule for project {project_id}')

  # Fetch VLAN attachments first so we can use them for both checks
  attachments = interconnect.get_vlan_attachments(context.project_id)
  attachments_by_key = {}
  if attachments:
    for v in attachments:
      attachments_by_key[(v.name, v.region)] = v

  mtu_exceeded_drops: Dict[Tuple[str, Optional[str]], Set[str]] = {}
  api_errors = []
  drop_reason = 'EXCEEDS_MTU'

  # Check 1: Packet drops from Monitoring
  if project_id not in query_results_per_project_id:
    report.add_skipped(project_resource, 'Monitoring data not prefetched for drop check')
  else:
    results = query_results_per_project_id[project_id]

    metric_checks = {
      'ic_egress': f'Interconnect egress {drop_reason}',
      'ic_ingress': f'Interconnect ingress {drop_reason}',
      'vpn_egress': 'VPN egress exceeds_mtu',
    }

    for check_key, description in metric_checks.items():
      result = results.get(check_key)

      if isinstance(result, Exception):
        api_errors.append(f'{check_key}: {result!r}')
        continue

      if not result:
        logging.debug(f'gcpdiag-rule-debug: Monitoring query for {check_key} returned no data.')
        continue

      for frozen_labels, ts_data in result.items():
        labels = ts_data.get('labels', {})
        # Programmatically find the correct label for resource name
        resource_name = labels.get('resource.attachment') or labels.get('resource.gateway_id')
        resource_region = labels.get('resource.region')
        if not resource_name:
          continue

        has_drops = False
        for val_list in ts_data.get('values', []):
          if val_list and val_list[0] > 0:
            has_drops = True
            break

        if has_drops:
          key = (resource_name, resource_region)
          if key not in mtu_exceeded_drops:
            mtu_exceeded_drops[key] = set()
          mtu_exceeded_drops[key].add(description)

    if not mtu_exceeded_drops and not api_errors:
      report.add_ok(
        project_resource,
        f'No {drop_reason} drops found on Interconnect or VPN in the last 7 days.',
      )
    else:
      for (resource_name, resource_region), reasons in sorted(mtu_exceeded_drops.items()):
        reason_str = ', '.join(sorted(list(reasons)))

        # Try to match with VlanAttachment to report with full path
        vlan_attachment = attachments_by_key.get((resource_name, resource_region))
        if vlan_attachment:
          res = vlan_attachment
        else:
          # Create a generic Resource object for the report.
          res = PathOnlyResource(project_id=project_id, full_path=resource_name)

        report.add_failed(
          res,
          reason=(
            'Potential MTU issue: Resource is experiencing packet drops:'
            f' {reason_str}. Verify MTU settings across the entire path'
            ' (VPC, Attachment/VPN, on-premises) and ensure PMTUD is'
            ' functional by allowing necessary ICMP messages.'
          ),
        )

    if api_errors:
      warning_msg = f'Partial errors during MTU metrics fetch: {"; ".join(api_errors)}'
      logging.warning(warning_msg)
      if not mtu_exceeded_drops:
        report.add_skipped(project_resource, warning_msg)

  # Check 2: VLAN attachment MTU vs VPC MTU
  if not attachments:
    report.add_skipped(None, 'no vlan attachments found for MTU config check')
  else:
    for vlan in attachments:
      try:
        vlan_router = network.get_router_by_name(
          project_id=context.project_id,
          region=vlan.region,
          router_name=vlan.router,
        )
        if not vlan_router:
          report.add_skipped(vlan, f'VLAN router {vlan.router} not found')
          continue

        vlan_network_name = vlan_router.get_network_name()
        vlan_network = network.get_network(
          project_id=context.project_id,
          network_name=vlan_network_name,
          context=context,
        )
        if not vlan_network:
          report.add_skipped(vlan, f'VLAN network {vlan_network_name} not found')
          continue

        if vlan.mtu != vlan_network.mtu:
          report.add_failed(
            vlan,
            None,
            f'MTU mismatch: VLAN Attachment MTU is {vlan.mtu}, but VPC'
            f' {vlan_network.name} MTU is {vlan_network.mtu}.',
          )
        else:
          # Only report OK if no other failures for this resource (by name/region)
          if (vlan.name, vlan.region) not in mtu_exceeded_drops:
            report.add_ok(
              vlan,
              f'VLAN Attachment and VPC {vlan_network.name} MTU match ({vlan.mtu}).',
            )
      except Exception as e:
        logging.warning(f'Error checking MTU for VLAN {vlan.name}: {e!r}')
        report.add_skipped(vlan, f'Error during config check: {e!r}')


# Clear cache for testing purposes if needed
def clear_cache():
  query_results_per_project_id.clear()
