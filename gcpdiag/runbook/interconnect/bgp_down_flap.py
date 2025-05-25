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
"""This runbook will analyze BGP down or flap issue"""

import json
from datetime import datetime

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import crm, interconnect, logs, network
from gcpdiag.runbook import op
from gcpdiag.runbook.interconnect import flags


def calculate_time(t1: str, t2: str) -> str:
  t11 = datetime.strptime(t1[:19], '%Y-%m-%dT%H:%M:%S')
  t22 = datetime.strptime(t2[:19], '%Y-%m-%dT%H:%M:%S')

  dt = t22 - t11
  dtstr = str(dt.total_seconds())
  return dtstr


def local_realtime_query(in_start_time, in_end_time, filter_str):
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time=in_start_time,
                               end_time=in_end_time,
                               filter_str=filter_str)
  return result


class BgpDownFlap(runbook.DiagnosticTree):
  """This rule book analyzes BGP down and BGP flap events in a region of a project.

  The following steps are executed:

  - Check BGP down status: Check if any vlan attachment has BGP down state.
  - Check Interconnect maintenance: Check if there are interconnect maintenance events
           are associated with the BGP down vlan attachments.
  - Check BGP flap status: Check if any BGP flaps happened.
  - Check Cloud Router maintenance: Check if there were Cloud Router maintenance events
           are associated with the BGP flaps.

  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.REGION: {
          'type': str,
          'help': 'The region where the vlan attachment is located',
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
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""

    start = BgpDownFlapStart()
    self.add_start(start)

    bgpdown = CheckBgpDown()
    iccheck = CheckInterconnectMaintenance()
    bgpflapcheck = CheckBgpFlap()
    crcheck = CheckCloudRouterMaintenance()

    self.add_step(parent=start, child=bgpdown)
    self.add_step(parent=bgpdown, child=iccheck)
    self.add_step(parent=start, child=bgpflapcheck)
    self.add_step(parent=bgpflapcheck, child=crcheck)

    self.add_end(BgpDownFlapEnd())


class BgpDownFlapStart(runbook.StartStep):
  """Check if the project and other parameters are valid and vlan attachments are available.

  This step starts the BGP issue debugging process by
  verifying the correct input parameters have been provided and checking to ensure
  that the following resources exist.
    - The Project
    - Region
    - The vlan attachments exist for the given project

  """

  template = 'bgp_down_flap::start'

  def execute(self):
    """Check provided parameters."""
    project_id = op.get(flags.PROJECT_ID)
    proj = crm.get_project(project_id)

    try:
      attachments = interconnect.get_vlan_attachments(project_id)
    except googleapiclient.errors.HttpError:
      op.add_skipped(proj,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project_id=project_id))
    else:
      for vlan in attachments:
        if vlan.region == op.get(flags.REGION):
          op.add_ok(proj,
                    reason=op.prep_msg(op.SUCCESS_REASON,
                                       project_id=project_id))
          return

      op.add_skipped(proj,
                     reason=op.prep_msg(op.SKIPPED_REASON_ALT1,
                                        region=op.get(flags.REGION),
                                        project_id=project_id))


class CheckBgpDown(runbook.Step):
  """Check if vlan attachments have BGP down state.

  Check if any vlan attachments have in BGP down state.
  """
  template = 'bgp_down_flap::bgpdown'

  def execute(self):
    """Check if there is vlan attachment has BGP down."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    attachments = interconnect.get_vlan_attachments(project.id)

    in_region = op.get(flags.REGION)

    # check each vlan attachment bgp state
    processed_routers = {}
    bgpdown_list = {}
    error_interconnects = ''
    for vlan in attachments:
      if vlan.region != in_region:
        continue
      router_name = vlan.router
      bgp_status = None

      # update bgp information in processed_routers
      if router_name in processed_routers:
        bgp_status = processed_routers[router_name]
      else:
        vlan_router_status = network.nat_router_status(project.id,
                                                       router_name=vlan.router,
                                                       region=vlan.region)
        bgp_status = vlan_router_status.bgp_peer_status
        processed_routers[router_name] = bgp_status

      # fetch bgp status for matching vlan attachment
      for item in bgp_status:
        if item['ipAddress'] == vlan.ipv4address:

          if item['state'] != 'Established':
            bgpdown_list.setdefault(vlan.interconnect, []).append(vlan.name)
            error_interconnects += vlan.interconnect + ','

    if len(error_interconnects) == 0:
      op.add_ok(project, op.prep_msg(op.SUCCESS_REASON))
    else:
      # display interconnect name with BGP down status
      for ic, vlans in bgpdown_list.items():
        for item in vlans:
          reason = op.prep_msg(op.FAILURE_REASON,
                               interconnect_name=ic,
                               attachment_name=item)
          op.info(reason)

      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
      if len(error_interconnects) > 0:
        error_interconnects = error_interconnects[:-1]
      op.put(flags.ERROR_LIST, error_interconnects)


class CheckInterconnectMaintenance(runbook.Step):
  """Check if interconnects with BGP down are in maintenance state.

  Check if any interconnects with BGP down are in maintenance state.
  """
  template = 'bgp_down_flap::interconnect_maintenance'

  def execute(self):
    """Check if any BGP down interconnects are in maintenance state."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    err_list = op.get(flags.ERROR_LIST)

    if err_list is None:
      op.add_skipped(
          project,
          'No BGP down events found, skip interconnect mainteance check')
      return

    interconnects = interconnect.get_links(op.get(flags.PROJECT_ID))
    if not interconnects:
      op.add_skipped(project, reason='no Inteconnect links found')
      return

    checklist = []
    for c in interconnects:
      icname = c.name

      if c.under_maintenance:
        checklist.append(icname)

    bgpdown_no_ic_maintenance_list = ''

    if len(checklist) > 0:
      tmperrorlist = err_list.split(',')
      for item in tmperrorlist:
        if item in checklist:
          continue
        else:
          bgpdown_no_ic_maintenance_list += item + ','

    if len(bgpdown_no_ic_maintenance_list) == 0:
      op.add_ok(project, op.prep_msg(op.SUCCESS_REASON))
    else:
      for item in bgpdown_no_ic_maintenance_list[:-1].split(','):
        reason = op.prep_msg(op.FAILURE_REASON, interconnect_name=item)
        op.info(reason)
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckCloudRouterMaintenance(runbook.Step):
  """Check if any Cloud Router had maintenance event.

  Check if any Cloud Router had maintenance event.
  Report BGP flaps without Cloud Router maintenance event.
  """
  template = 'bgp_down_flap::cloud_router_maintenance'

  def execute(self):
    """Check if the Cloud Router had maintenance event."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    cr_list = []
    bgp_flaps = json.loads(op.get(flags.BGP_FLAP_LIST))

    for router_id, times in bgp_flaps.items():
      t1 = times[0].split(',')[0][:19]
      t2 = times[0].split(',')[1][:19]

      t11 = datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S')
      t22 = datetime.strptime(t2, '%Y-%m-%dT%H:%M:%S')
      filter_str = [
          'resource.type="gce_router"', '"Maintenance of router task"'
      ]
      region = op.get(flags.REGION)
      if region:
        filter_str.append(f'resource.labels.region="{region}"')
      filter_str = '\n'.join(filter_str)

      serial_log_entries = None
      serial_log_entries = local_realtime_query(t11, t22, filter_str)

      if serial_log_entries:
        pass
      else:
        # No CR maintenance event found for the BGP flap, add to error list
        errstr = router_id + ', ' + t1 + ', ' + t2
        cr_list.append(errstr)

    # cr_list contains router_id with BGP flap but no maintenance event
    # it can be caused by router device error, configuration change or control plane change
    # further debugging is needed
    if len(cr_list) > 0:
      op.info('')
      op.info(
          'The following router id had BGP flaps without Cloud Router Maintenance:'
      )
      for item in cr_list:
        op.info(item)
      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project, op.prep_msg(op.SUCCESS_REASON))


class CheckBgpFlap(runbook.Step):
  """Check if any BGP flap events, report error flaps with duration over 60 seconds.

  Check if any BGP flap events, report error flaps with duration over 60 seconds.
  """

  template = 'bgp_down_flap::bgpflap'

  def execute(self):
    """Check if there are BGP flap events."""
    project = crm.get_project(op.get(flags.PROJECT_ID))

    filter_str = [
        'resource.type="gce_router"', '"BGP "', '("came up" OR "went down")'
    ]

    region = op.get(flags.REGION)
    if region:
      filter_str.append(f'resource.labels.region="{region}"')
    filter_str = '\n'.join(filter_str)

    last_down_time = {}
    router_logs = {}
    err_router_logs = {}
    bgp_flaps = {}

    serial_log_entries = local_realtime_query(op.get(flags.START_TIME),
                                              op.get(flags.END_TIME),
                                              filter_str)

    # ensure the serial_log_entries have oldest timestamp first
    if len(serial_log_entries) > 1:
      t1 = get_path(serial_log_entries[0], ('timestamp'), default=None)
      t2 = get_path(serial_log_entries[-1], ('timestamp'), default=None)
      delta = calculate_time(t1, t2)
      if delta[0] == '-':
        reversed_list = []
        for item in serial_log_entries:
          reversed_list.insert(0, item)
        serial_log_entries = reversed_list

    for item in serial_log_entries:
      errflag = False

      payload = get_path(item, ('textPayload'), default=None)
      timestamp = get_path(item, ('timestamp'), default=None)
      router_id = get_path(item, ('resource', 'labels', 'router_id'),
                           default=None)
      tmp = payload.split('peering with ')[1]
      ip = tmp.split()[0].strip()

      event = 'went down'
      if 'came up' in tmp:
        event = 'came up'

      logentry = []
      logentry.append(router_id)
      logentry.append(ip)
      logentry.append(event)
      logentry.append(timestamp)

      if 'came up' in payload:
        if router_id in last_down_time:
          downtime = last_down_time[router_id][0]
          last_down_time[router_id] = []

          delta = calculate_time(downtime, timestamp)

          logentry.append(delta)
          if int(delta.split('.', maxsplit=1)[0]) > 60:
            # BGP flaps over 60s is an error
            errflag = True
          else:
            # BGP flaps less than 60s need further check
            # save router_id, down and up timestamps for next step Cloud Router maintenance check
            down_up_times = downtime + ',' + timestamp
            bgp_flaps.setdefault(router_id, []).append(down_up_times)
      else:
        last_down_time.setdefault(router_id, []).append(timestamp)

      router_logs.setdefault(router_id, []).append(logentry)
      if errflag:
        lastlogentry = router_logs[router_id][-2]
        err_router_logs.setdefault(router_id, []).append(lastlogentry)
        err_router_logs.setdefault(router_id, []).append(logentry)

    op.put(flags.BGP_FLAP_LIST, json.dumps(bgp_flaps))

    if len(router_logs) > 0:
      if len(err_router_logs) == 0:
        op.add_uncertain(project,
                         reason=op.prep_msg(op.UNCERTAIN_REASON,
                                            project_id=project.id),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))
      else:
        # display BGP flaps with time duration over 60s.
        op.info('')
        op.info('There are Cloud Router BGP flaps over 60s: ')

        errstr = ''
        for key, value in err_router_logs.items():
          for item in value:
            tmp = str(item)
            op.info(tmp)
            if key not in errstr:
              errstr += key + ','
        errstr = errstr[:-1]

        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         project_id=project.id),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))
    else:
      op.add_ok(project, reason=op.prep_msg(op.SUCCESS_REASON))


class BgpDownFlapEnd(runbook.EndStep):
  """Concludes the diagnostics process.

  The following are considered error and need further debugging:

  1> BGP down events found without interconnect maintenance
  2> BGP flaps with duration over 60 seconds
  3> BGP flaps with duration less than 60 seconds but no Cloud Router maintenance event

  Please contact GCP support for further debugging

  """

  def execute(self):
    """Finalizing connectivity diagnostics."""
    op.info('If any further debugging is needed, '
            'consider please contact GCP support for further troubleshooting')
