# Copyright 2025 Google LLC
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
"""Runbook for diagnosing issues with a Cloud VPN Tunnel."""

from datetime import datetime

from googleapiclient import errors as gapi_errors

from gcpdiag import runbook, utils
from gcpdiag.queries import crm, logs, monitoring, vpn
from gcpdiag.runbook import op
from gcpdiag.runbook.vpn import constants, flags


class VpnTunnelCheck(runbook.DiagnosticTree):
  """Runbook for diagnosing issues with a Cloud VPN Tunnel.

This runbook performs several checks on a specified Cloud VPN tunnel:
-   **VPN Tunnel Status Check**: Verifies if the VPN tunnel is in an
    'ESTABLISHED' state.
-   **Tunnel Down Status Reason**: If the tunnel is not established, it queries
    Cloud Logging for specific error messages and provide remediations .
-   **Tunnel Packet Drop Check**: If the tunnel is established, it examines
    monitoring metrics for various types of packet drops (e.g., due to MTU,
    invalid SA, throttling) and provides remediation based on the drop reason.
-   **Tunnel Packet Utilization Check**: Analyzes packet rates to identify if
    the tunnel is hitting max packet per second limits.
"""

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.REGION: {
          'type': str,
          'help': 'The region where the VPN Tunnel is located',
          'required': True,
      },
      flags.NAME: {
          'type': str,
          'help': 'Name of the VPN Tunnel',
          'required': True,
      },
      flags.START_TIME: {
          'type':
              datetime,
          'help':
              'The start window to investigate BGP flap. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME: {
          'type':
              datetime,
          'help':
              'The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.TUNNEL: {
          'type': str,
          'help': 'This Flag will be added Automatically',
          'required': False,
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = VpnTunnelStatus()
    # add them to your tree
    self.add_start(start)
    self.add_step(parent=start, child=TunnelDownStatusReason())
    self.add_step(parent=start, child=TunnelPacketsDropCheck())
    self.add_step(parent=start, child=TunnelPacketsUtilizationCheck())
    self.add_end(VpnTunnelCheckEnd())


class VpnTunnelStatus(runbook.StartStep):
  """Checking the VPN Tunnel status"""

  template = 'vpn_check::tunnel'

  def execute(self):
    """Start the tunnel status api call"""
    proj = crm.get_project(op.get(flags.PROJECT_ID))
    if proj:
      op.info(f'name: {proj.name}, id: {proj.id}, number: {proj.number}')

    try:
      project_id = op.get(flags.PROJECT_ID)
      name = op.get(flags.NAME)
      region = op.get(flags.REGION)

      tunnel = vpn.get_vpn(project_id, name, region)
      op.put(flags.TUNNEL, tunnel.full_path)

      if tunnel.status == 'ESTABLISHED':
        op.add_ok(tunnel,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     tunnel=tunnel,
                                     project=project_id))
      else:
        op.add_failed(tunnel,
                      reason=op.prep_msg(
                          op.FAILURE_REASON,
                          tunnel=tunnel,
                          project=project_id,
                          issue=f'Tunnel status is {tunnel.status}',
                          status=tunnel.status),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              tunnel=tunnel,
                                              project=project_id,
                                              status=tunnel.status))
      return True

    except (gapi_errors.HttpError, utils.GcpApiError) as e:
      op.add_skipped(
          proj,
          reason=op.prep_msg(
              op.SKIPPED_REASON,
              tunnel=name,
              project=project_id,
              issue=(f'API call failed {e} : Check that the provided '
                     'tunnel and project information are correct')))
      return False


def _get_combined_metric_data(project_id, query_ingress, query_egress,
                              start_time, end_time):
  """Helper to fetch and merge ingress/egress metrics by timestamp."""
  try:
    m_ingress = monitoring.queryrange(project_id, query_ingress, start_time,
                                      end_time)
  except (gapi_errors.HttpError, monitoring.GcpApiError) as e:
    op.warning(f"Failed to query ingress metrics: {e}")
    m_ingress = {}
  try:
    m_egress = monitoring.queryrange(project_id, query_egress, start_time,
                                     end_time)
  except (gapi_errors.HttpError, monitoring.GcpApiError) as e:
    op.warning(f"Failed to query egress metrics: {e}")
    m_egress = {}

  def extract_values(response):
    results = response.get('data', {}).get('result', [])
    if not results or 'values' not in results[0]:
      return {}
    return {t: float(v) for t, v in results[0].get('values', [])}

  res_in = extract_values(m_ingress)
  res_out = extract_values(m_egress)

  if not res_in and not res_out:
    return []

  all_timestamps = set(res_in.keys()).union(set(res_out.keys()))

  combined = []
  for ts in all_timestamps:
    val_in = res_in.get(ts, 0.0)
    val_out = res_out.get(ts, 0.0)
    combined.append({
        'timestamp': datetime.fromtimestamp(ts).isoformat(),
        'total': val_in + val_out
    })
  return combined


class TunnelPacketsUtilizationCheck(runbook.Step):
  """Checking the VPN Tunnel Packet Utilization"""
  template = 'vpn_check::packet_check'

  def execute(self):
    """Start the tunnel Packet api call"""
    # tunnel = op.get(flags.TUNNEL)
    project_id = op.get(flags.PROJECT_ID)
    name, region = op.get(flags.NAME), op.get(flags.REGION)
    try:
      tunnel = vpn.get_vpn(project_id, name, region)
    except utils.GcpApiError as e:
      op.add_skipped(None,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project=project_id,
                                        issue=f'Failed to get tunnel: {e}'))
      return

    if tunnel.status != 'ESTABLISHED':
      op.add_skipped(tunnel,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project=project_id,
                                        issue='Tunnel not Established'))
      return

    q_in = (
        f'sum(rate({{"__name__"="vpn.googleapis.com/network/received_packets_count",'
        f'"tunnel_name"="{name}","region"="{region}"}}[1m]))')
    q_out = (
        f'sum(rate({{"__name__"="vpn.googleapis.com/network/sent_packets_count",'
        f'"tunnel_name"="{name}","region"="{region}"}}[1m]))')

    combined_data = _get_combined_metric_data(project_id, q_in, q_out,
                                              op.get(flags.START_TIME),
                                              op.get(flags.END_TIME))

    if not combined_data:
      op.add_failed(tunnel,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       tunnel=tunnel,
                                       project=project_id,
                                       issue='has no traffic'),
                    remediation=op.prep_msg(
                        op.FAILURE_REMEDIATION,
                        remediations='Check route configuration'))
      return

    exceeded = [
        d for d in combined_data
        if d['total'] >= constants.PACKET_PER_SECOND_LIMIT
    ]

    if exceeded:
      op.add_failed(
          tunnel,
          reason=op.prep_msg(op.FAILURE_REASON,
                             tunnel=tunnel,
                             project=project_id,
                             issue=f'Reached limit {len(exceeded)} times'),
          remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                  remediations='Reduce rate or add tunnels'))
    else:
      op.add_ok(tunnel,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   tunnel=tunnel,
                                   project=project_id))


class TunnelPacketsDropCheck(runbook.Step):
  """Checking the VPN Tunnel Packet Drop """
  template = 'vpn_check::packet_drop_check'

  DROP_REASONS = {
      'dont_fragment_icmp': {
          'reason':
              'Dropped ICMP packet larger than MTU with DF bit set (PMTUD).',
          'remediation':
              'Ensure ICMP packets for PMTUD do not exceed effective MTU.'
      },
      'dont_fragment_nonfirst_fragment': {
          'reason':
              'Non-first fragment of UDP/ESP packet exceeds MTU with DF bit set.',
          'remediation':
              'Verify application fragmentation handling or reduce IP packet size.'
      },
      'exceeds_mtu': {
          'reason':
              'First fragment of UDP/ESP packet exceeds MTU with DF bit set.',
          'remediation':
              'Reduce effective MTU (usually 1460 bytes) or permit fragmentation.'
      },
      'invalid': {
          'reason':
              'Dropped due to invalid state (corruption or unexpected sequence).',
          'remediation':
              'Review peer VPN config and capture traffic to check for corruption.'
      },
      'sa_expired': {
          'reason':
              'Packet used unknown or expired SA (negotiation failure).',
          'remediation':
              'Sync IKE/IPsec SA lifetimes on both peers; consider a tunnel reset.'
      },
      'sequence_number_lost': {
          'reason':
              'Sequence number significantly larger than expected (packet loss).',
          'remediation':
              'Investigate network path for congestion or connectivity issues.'
      },
      'suspected_replay': {
          'reason':
              'ESP packet received with a sequence number already processed.',
          'remediation':
              'Check for network devices (load balancers) duplicating or reordering packets.'
      },
      'throttled': {
          'reason':
              'Packet dropped due to excessive load on Cloud VPN gateway.',
          'remediation':
              'Reduce traffic or provision additional tunnels/Cloud Interconnect.'
      },
      'unknown': {
          'reason':
              'Packet dropped for an uncategorized reason.',
          'remediation':
              'Collect logs from both peers and contact Google Cloud support.'
      }
  }

  def execute(self):
    """Start the tunnel Packet drop api call"""

    # tunnel = op.get(flags.TUNNEL)
    project_id = op.get(flags.PROJECT_ID)
    name = op.get(flags.NAME)
    region = op.get(flags.REGION)
    end_time = op.get(flags.END_TIME)
    start_time = op.get(flags.START_TIME)
    try:
      tunnel = vpn.get_vpn(project_id, name, region)
    except utils.GcpApiError as e:
      op.add_skipped(None,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project=project_id,
                                        issue=f'Failed to get tunnel: {e}'))
      return

    if tunnel.status != 'ESTABLISHED':
      op.add_skipped(tunnel,
                     reason=op.prep_msg(
                         op.SKIPPED_REASON,
                         project=project_id,
                         issue='Check Skipped: Tunnel not Established'))
      return

    issue_found = False
    flows = [('egress', 'sent_packets_count'),
             ('ingress', 'received_packets_count')]

    for direction_label, metric_suffix in flows:
      query = (
          f'sum by (status) (rate({{"__name__" = "vpn.googleapis.com/network/{metric_suffix}",'
          f'"monitored_resource" = "vpn_gateway","tunnel_name" = "{name}",'
          f'"region" = "{region}"}}[1m]))')
      try:
        status_drop = monitoring.queryrange(project_id, query, start_time,
                                            end_time)
      except (gapi_errors.HttpError, monitoring.GcpApiError) as e:
        op.warning(
            f"Failed to query packet drop metrics for {direction_label}: {e}")
        continue
      for metric_data in status_drop.get('data', {}).get('result', []):
        status = metric_data['metric'].get('status')

        if status == 'successful' or status not in self.DROP_REASONS:
          continue

        drops = [[datetime.fromtimestamp(t).isoformat(),
                  float(v)] for t, v in metric_data['values'] if float(v) >= 1]

        if drops:
          issue_found = True
          diag = self.DROP_REASONS[status]
          reason_msg = diag['reason']
          base_issue = (
              f'Project {project_id} on VPN {name} has {direction_label} drops '
              f'({status}). Times: {drops}. Reason: {reason_msg}')

          op.add_failed(tunnel,
                        reason=op.prep_msg(op.FAILURE_REASON,
                                           tunnel=tunnel,
                                           project=project_id,
                                           issue=base_issue),
                        remediation=op.prep_msg(
                            op.FAILURE_REMEDIATION,
                            tunnel=tunnel,
                            project=project_id,
                            remediations=diag['remediation']))

    if not issue_found:
      op.add_ok(tunnel,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   tunnel=tunnel,
                                   project=project_id))


class TunnelDownStatusReason(runbook.Step):
  """Checks the status of the tunnel and provides reasons for failure."""

  template = 'vpn_check::log_explorer'

  def execute(self):
    """Check VPN tunnel logs and status."""
    project_id = op.get(flags.PROJECT_ID)
    name, region = op.get(flags.NAME), op.get(flags.REGION)
    end_time = op.get(flags.END_TIME)
    start_time = op.get(flags.START_TIME)
    try:
      tunnel = vpn.get_vpn(project_id, name, region)
    except utils.GcpApiError as e:
      op.add_skipped(None,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project=project_id,
                                        issue=f'Failed to get tunnel: {e}'))
      return

    reasons = [
        '"establishing IKE_SA failed, peer not responding"',
        '"Remote traffic selectors narrowed"',
        '"Local traffic selectors narrowed"', '"Proposal mismatch in CHILD SA"',
        '("Starting VPN Task maintenance" AND "VPN Task maintenance Completed")'
    ]

    filter_str = (f'resource.type = "vpn_gateway" AND '
                  f'labels.tunnel_id = "{tunnel.id}" AND '
                  f"({' OR '.join(reasons)})")

    fetched_logs = logs.realtime_query(project_id=project_id,
                                       filter_str=filter_str,
                                       start_time=start_time,
                                       end_time=end_time)

    log_text = ' '.join([l.message for l in fetched_logs])
    found_issue = False

    if 'establishing IKE_SA failed' in log_text:
      found_issue = True
      op.add_failed(
          tunnel,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              tunnel=tunnel,
              project=project_id,
              issue=
              'IKE_SA failure: Peer not responding. Possible firewall blocking traffic.'
          ),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              remediations=
              'Ensure UDP ports 500/4500 are open, and check peer reachability.'
          ))

    if 'Remote traffic selectors narrowed' in log_text:
      found_issue = True
      op.add_failed(
          tunnel,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              tunnel=tunnel,
              project=project_id,
              issue='Remote traffic selectors narrowed by peer.'),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              remediations=
              'Match Cloud VPN remote selectors with peer\'s local selectors.'))

    if 'Local traffic selectors narrowed' in log_text:
      found_issue = True
      op.add_failed(
          tunnel,
          reason=op.prep_msg(op.FAILURE_REASON,
                             tunnel=tunnel,
                             project=project_id,
                             issue='Local traffic selectors mismatch.'),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              remediations=
              'Ensure Cloud VPN local selectors match peer\'s remote selectors.'
          ))

    if 'Proposal mismatch in CHILD SA' in log_text:
      found_issue = True
      op.add_failed(
          tunnel,
          reason=op.prep_msg(op.FAILURE_REASON,
                             tunnel=tunnel,
                             project=project_id,
                             issue='IPsec Phase 2 proposal mismatch.'),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              remediations=
              'Align Phase 2 settings (Encryption/DH groups) on both ends.'))

    if 'VPN Task maintenance' in log_text:
      found_issue = True
      op.add_failed(
          tunnel,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              tunnel=tunnel,
              project=project_id,
              issue='VPN maintenance occurred during this window.'),
          remediation=op.prep_msg(
              op.FAILURE_REMEDIATION,
              remediations=
              'Tunnels usually recover automatically. Contact Support if it stays down.'
          ))

    if not found_issue:
      if tunnel.status != 'ESTABLISHED':
        op.add_failed(
            tunnel,
            reason=op.prep_msg(
                op.FAILURE_REASON,
                tunnel=tunnel,
                project=project_id,
                issue=
                'Tunnel is not established, but no specific error logs were found.'
            ),
            remediation=op.prep_msg(
                op.FAILURE_REMEDIATION,
                remediations=
                'Try broadening the timeframe or checking the peer device logs.'
            ))
      else:
        op.add_ok(tunnel,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     tunnel=tunnel,
                                     project=project_id))

    return True


class VpnTunnelCheckEnd(runbook.EndStep):
  """Concludes the diagnostics process."""

  def execute(self):
    """Finalizing connectivity diagnostics."""
    op.info('If any further debugging is needed, '
            'consider please contact GCP support for further troubleshooting')
