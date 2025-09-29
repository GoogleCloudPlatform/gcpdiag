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
import re
from datetime import datetime, timezone

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import runbook
from gcpdiag.queries import crm, interconnect, logs, network
from gcpdiag.runbook import op
from gcpdiag.runbook.interconnect import flags

# GRACEFUL_RESTART_TIMER is set to 120 seconds, which is current Cloud Router default.
# However, this value can vary based on GCP Cloud Router configuration.
GRACEFUL_RESTART_TIMER = 120


def get_time_delta(t1: str, t2: str) -> str:
  """
  Calculates the time difference between two ISO 8601 formatted time strings.

  Args:
    t1: The ISO 8601 formatted start time string.
    t2: The ISO 8601 formatted time end time string.

  Returns:
    A string representing the time difference in seconds, rounded to two decimal places.
  """
  t11 = datetime.fromisoformat(str(t1)).replace(tzinfo=timezone.utc)
  t22 = datetime.fromisoformat(str(t2)).replace(tzinfo=timezone.utc)

  dt = t22 - t11
  dtstr = str(round(dt.total_seconds(), 2))
  return dtstr


def local_realtime_query(in_start_time, in_end_time, filter_str):
  """
  Run cloud logging query to get cloud logging details.

  Args:
    in_sart_time: The ISO 8601 formatted start time string.
    in_end_time:  The ISO 8601 formatted time end time string.
    filter_str:   The filter strings in cloud logging query.

  Returns:
    A dqueue collection containing cloud logging query output entries.
  """
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time=in_start_time,
                               end_time=in_end_time,
                               filter_str=filter_str)
  return result


class BgpDownFlap(runbook.DiagnosticTree):
  """This runbook analyzes BGP down and BGP flap events for a GCP project in a clolud region.

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
      flags.ATTACHMENT_NAME: {
          'type': str,
          'help':
              'The attachment name(s) as comma-separated values or a regular expression. '
              'eg: vlan1,vlan2 or vlan.* or .* for all attachments',
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
    attachments_in = op.get(flags.ATTACHMENT_NAME).rstrip(', \n')
    # regexp or comma separated names
    attachments_in_list = attachments_in.split(',')
    found_attachment_list = []

    try:
      attachments = interconnect.get_vlan_attachments(project_id)
    except googleapiclient.errors.HttpError:
      op.add_skipped(proj,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project_id=project_id))
    else:
      for vlan in attachments:
        if vlan.region == op.get(flags.REGION):
          if vlan.name in attachments_in_list or re.search(
              attachments_in, vlan.name):
            found_attachment_list.append(vlan.name)

      if len(found_attachment_list) >= len(attachments_in_list):
        op.put(flags.ATTACHMENT_LIST, ','.join(found_attachment_list))
        op.add_ok(proj,
                  reason=op.prep_msg(op.SUCCESS_REASON,
                                     total_num=len(found_attachment_list),
                                     region=op.get(flags.REGION),
                                     project_id=project_id))

        return

      err_names = ''
      for item in attachments_in_list:
        if item not in found_attachment_list:
          err_names += item + ','

      err_names = err_names.rstrip(',')
      op.add_skipped(proj,
                     reason=op.prep_msg(op.SKIPPED_REASON_ALT1,
                                        err_names=err_names,
                                        region=op.get(flags.REGION),
                                        project_id=project_id))


class CheckBgpDown(runbook.Step):
  """Check if vlan attachments have BGP down state.

  Check if any vlan attachments have in BGP down state.
  """
  template = 'bgp_down_flap::bgpdown'

  def execute(self):
    """
    Check if there is vlan attachment has BGP down.

    """
    project_id = op.get(flags.PROJECT_ID)
    project = crm.get_project(op.get(flags.PROJECT_ID))
    attachments = interconnect.get_vlan_attachments(project.id)
    vlan_router_map = {}

    in_region = op.get(flags.REGION)
    found_attachment_list = op.get(flags.ATTACHMENT_LIST).split(',')

    # check each vlan attachment bgp state
    processed_routers = {}
    bgpdown_list = {}
    vlan_router_map = {}
    error_interconnects = ''
    for vlan in attachments:
      if vlan.region != in_region or vlan.name not in found_attachment_list:
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
            vlan_router_map[vlan.name] = vlan.router
            error_interconnects += vlan.interconnect + ','

    if len(error_interconnects) == 0:
      op.put(flags.ERROR_LIST, '')
      op.add_ok(
          project,
          op.prep_msg(op.SUCCESS_REASON,
                      region=op.get(flags.REGION),
                      project_id=project_id))
    else:
      # display interconnect name with BGP down status
      reason = '\n\t Attachments with BGP down status:\n'
      for ic, vlans in bgpdown_list.items():
        for item in vlans:
          reason += op.prep_msg(op.FAILURE_REASON,
                                interconnect_name=ic,
                                attachment_name=item,
                                router_name=vlan_router_map[item])

      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1, reason=reason),
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

    if len(err_list) == 0:
      op.add_skipped(project,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        region=op.get(flags.REGION),
                                        project_id=project.id))
      return

    interconnects = interconnect.get_links(project.id)
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
    else:
      bgpdown_no_ic_maintenance_list = err_list

    bgpdown_no_ic_maintenance_list = bgpdown_no_ic_maintenance_list.rstrip(',')

    if len(bgpdown_no_ic_maintenance_list) == 0:
      op.add_ok(project, op.prep_msg(op.SUCCESS_REASON))
    else:
      reason = '\n\t BGP down details:\n'
      for item in bgpdown_no_ic_maintenance_list.split(','):
        reason += op.prep_msg(op.FAILURE_REASON, interconnect_name=item)

      # interconnect BGP down can be caused by various reasons
      # The first step is to check if there is planned maintenance event
      remediation_details = """ \n\t Suggested Remediations:
               *   Check on-prem PF interface status towards on-prem router
               *   Check RX/TX light level
               *   Check cloud console interconnect details or cloud logging
               *   Check other potential issues, or Contact Google Cloud Support."""

      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1, reason=reason),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            remediation=remediation_details))


class CheckCloudRouterMaintenance(runbook.Step):
  """Check if any Cloud Router had maintenance event.

  Check if any Cloud Router had maintenance event.
  Report BGP flaps without Cloud Router maintenance event.
  """
  template = 'bgp_down_flap::cloud_router_maintenance'

  def execute(self):
    """Check if the Cloud Router had maintenance event."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    bgp_flaps = json.loads(op.get(flags.BGP_FLAP_LIST))

    uncertain = False
    checklist = []
    # List all router_id with uncertain BGP flaps
    for key, value in bgp_flaps.items():
      if value['uncertain_flag'] == 'True':
        uncertain = True
        router_id = key.split('--')[0]
        if router_id not in checklist:
          checklist.append(router_id)

    # Skip if no uncertain BGP flas need to be checked
    if uncertain is False:
      op.add_skipped(project,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        region=op.get(flags.REGION),
                                        project_id=project.id))
      return

    # Fetch cloud logging router maintenance events
    # maintenance_list :
    # key : router_id
    # value : list of maintenance event timestamps
    maintenance_list = {}
    for router_id in checklist:
      filter_str = [
          'resource.type="gce_router"', '"Maintenance of router task"'
      ]
      region = op.get(flags.REGION)
      if region:
        filter_str.append(f'resource.labels.region="{region}"')

      # Minor Concern: The filter string for Cloud Logging, created by joining IP
      # addresses with "OR", could potentially become very long if there are many
      # attachments. While unlikely to hit the absolute maximum, it's worth
      # keeping in mind.
      filter_str.append(f'resource.labels.router_id="{router_id}"')
      filter_str = '\n'.join(filter_str)

      start_time = op.get(flags.START_TIME)
      end_time = op.get(flags.END_TIME)

      # Ensure times are timezone-aware UTC
      if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=datetime.timezone.utc)
      if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=datetime.timezone.utc)

      serial_log_entries = None
      serial_log_entries = local_realtime_query(start_time, end_time,
                                                filter_str)

      times = []
      for item in serial_log_entries:
        payload = get_path(item, ('textPayload'), default=None)
        log_region = get_path(item, ('resource', 'labels', 'region'),
                              default=None)

        if log_region != region:
          continue

        if 'Maintenance of router task' not in payload:
          continue

        timestamp = get_path(item, ('timestamp'), default=None)
        times.append(timestamp)

      maintenance_list[router_id] = times

    # Find BGP flaps that do not have allgined router maintenance events
    # err_list
    #   key : router_id--ip
    #   value: list of BGP flap events without maintenance events
    err_list = {}
    for key, value in bgp_flaps.items():
      # check short duration uncertain BGP flaps
      if value['uncertain_flag'] != 'True':
        continue
      router_id = value['router_id']
      if router_id not in maintenance_list or len(
          maintenance_list[router_id]) == 0:
        err_list[key] = value['events']
        continue

      events = value['events']
      for oneflap in events:
        tmpstr = oneflap[0]
        t1 = tmpstr.split(',')[1]
        t2 = tmpstr.split(',')[3]
        okevent = False
        for cr_time in maintenance_list[router_id]:
          delta1 = get_time_delta(t1, cr_time)
          delta2 = get_time_delta(cr_time, t2)

          # check if there is router maintenance event between the BGP flap start and end time
          if delta1[0] != '-' and delta2[0] != '-':
            okevent = True
            break

        if not okevent:
          err_list.setdefault(key, []).append(oneflap)

    # error_list contains router_id with BGP flaps but no maintenance event
    if len(err_list) > 0:
      reason = '\n'
      for key, value in err_list.items():
        flap_details = '\n\t\tBGP flap details:'
        for item in value:
          flap_details = flap_details + '\n\t\t' + ','.join(item)
        flap_details += '\n'

        reason += op.prep_msg(op.FAILURE_REASON,
                              router_id=bgp_flaps[key]['router_id'],
                              local_ip=bgp_flaps[key]['local_ip'],
                              remote_ip=bgp_flaps[key]['remote_ip'],
                              router_name=bgp_flaps[key]['router_name'],
                              attachment=bgp_flaps[key]['attachment_name'],
                              project_id=bgp_flaps[key]['project_id'],
                              flap_details=flap_details)

      example_query = """ \nExample query:
            resource.type="gce_router"
            "Maintenance of router task" OR ("came up" OR "went down")
            resource.labels.region="<region>"
            r.esource.labels.router_id="<router_id>"
            """

      op.add_failed(project,
                    reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                       timer=GRACEFUL_RESTART_TIMER,
                                       reason=reason),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            timer=GRACEFUL_RESTART_TIMER,
                                            example_query=example_query))
    else:
      op.add_ok(project,
                op.prep_msg(op.SUCCESS_REASON, timer=GRACEFUL_RESTART_TIMER))


class CheckBgpFlap(runbook.Step):
  """Check if any BGP flap events, report error flaps with duration over 60 seconds.

  Check if any BGP flap events, report error flaps with duration over 60 seconds.
  """

  template = 'bgp_down_flap::bgpflap'

  def execute(self):
    """Check if there are BGP flap events."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    region = op.get(flags.REGION)

    attachments_in = op.get(flags.ATTACHMENT_NAME).rstrip(
        ', \n')  # regexp or comma separated names
    attachments_in_list = attachments_in.split(',')
    found_attachment_list = []

    try:
      attachments = interconnect.get_vlan_attachments(project.id)
    except googleapiclient.errors.HttpError:
      op.add_skipped(project,
                     reason=op.prep_msg(op.SKIPPED_REASON,
                                        project_id=project.id))

    for vlan in attachments:
      if vlan.region == op.get(flags.REGION):
        if vlan.name in attachments_in_list or re.search(
            attachments_in, vlan.name):
          found_attachment_list.append(vlan.name)

    peerip_router_map = {}
    vlan_ipv4_list = []

    attachments = interconnect.get_vlan_attachments(project.id)

    for vlan in attachments:
      if vlan.region != region or vlan.name not in found_attachment_list:
        continue
      vlan_ipv4_list.append(vlan.remoteip)

      # peerip_router_map
      #   key :  vlan.remoteIp
      #   value: router_name, localIp, reomoteIp, interconnect, region, project_id
      key = vlan.remoteip
      peerip_router_map.setdefault(key, []).append(vlan.router)
      peerip_router_map[key].append(vlan.ipv4address)
      peerip_router_map[key].append(vlan.remoteip)
      peerip_router_map[key].append(vlan.interconnect)
      peerip_router_map[key].append(region)
      peerip_router_map[key].append(project.id)
      peerip_router_map[key].append(vlan.name)

    filter_str = [
        'resource.type="gce_router"', '"BGP "', '("came up" OR "went down")'
    ]

    # cloud logging query takes time
    # run query once to get logging for all attachments
    ipstr = ''
    for item in vlan_ipv4_list:
      ipstr += '"' + item + '"' + ' OR '
    ipstr = ipstr[:-3]

    # Minor Concern: The filter string for Cloud Logging, created by joining IP
    # addresses with "OR", could potentially become very long if there are many
    # attachments. While unlikely to hit the absolute maximum, it's worth
    # keeping in mind.
    filter_str.append(ipstr)
    if region:
      filter_str.append(f'resource.labels.region="{region}"')
    filter_str = '\n'.join(filter_str)

    last_down_time = {}
    router_logs = {}
    err_router_logs = {}

    start_time = op.get(flags.START_TIME)
    end_time = op.get(flags.END_TIME)

    # Ensure times are timezone-aware UTC
    if start_time.tzinfo is None:
      start_time = start_time.replace(tzinfo=datetime.timezone.utc)
    if end_time.tzinfo is None:
      end_time = end_time.replace(tzinfo=datetime.timezone.utc)

    serial_log_entries = None
    serial_log_entries = local_realtime_query(start_time, end_time, filter_str)

    # ensure the serial_log_entries have oldest timestamp first
    if len(serial_log_entries) > 1:
      t1 = get_path(serial_log_entries[0], ('timestamp'), default=None)
      t2 = get_path(serial_log_entries[-1], ('timestamp'), default=None)
      delta = get_time_delta(t1, t2)
      if delta[0] == '-':
        reversed_list = []
        for item in serial_log_entries:
          reversed_list.insert(0, item)
        serial_log_entries = reversed_list

    # get bgp flaps events from logging query output
    #    router_logs     : all bgp flaps
    #    err_router_logs : bgp flaps longer than GRACEFUL_RESTART_TIMER
    for item in serial_log_entries:
      errflag = False
      payload = get_path(item, ('textPayload'), default=None)
      timestamp = get_path(item, ('timestamp'), default=None)
      router_id = get_path(item, ('resource', 'labels', 'router_id'),
                           default=None)

      log_region = get_path(item, ('resource', 'labels', 'region'),
                            default=None)

      if log_region != region:
        continue

      if not 'BGP Event: BGP peering with' in payload:
        continue

      tmp = payload.split('peering with ')[1]
      ip = tmp.split()[0].strip()

      # unique identify BGP session by using router_id and ip
      router_ip_key = router_id + '--' + ip

      logentry = []
      if 'came up' in payload:
        if router_ip_key in last_down_time:
          downtime = last_down_time[router_ip_key][0]
          last_down_time[router_ip_key] = []

          delta = get_time_delta(downtime, timestamp)
          down_up_times = 'went down,' + downtime + ',came up,' + timestamp
          logentry.append(down_up_times)
          logentry.append(delta)
          if int(delta.split('.', maxsplit=1)[0]) > GRACEFUL_RESTART_TIMER:
            # BGP flaps longer than GRACEFUL_RESTART_TIMER will cause data plane issue.
            errflag = True
            logentry.append('Error')
          else:
            # If there is a normal maintenance event align with a flap, we can ignore the BGP flap.
            logentry.append('Uncertain')
          router_logs.setdefault(router_ip_key, []).append(logentry)
      else:
        last_down_time.setdefault(router_ip_key, []).append(timestamp)

      if errflag:
        err_router_logs.setdefault(router_ip_key, []).append(logentry)

    # cross reference BGP data
    # get vlan information from API call
    # get BGP and router information from logging
    bgpdata = {}
    for key, value in router_logs.items():
      remote_ip = key.split('--')[1]
      router_id = key.split('--')[0]

      onedata = {}
      onedata['router_id'] = router_id
      onedata['remote_ip'] = remote_ip
      onedata['events'] = value
      onedata['uncertain_flag'] = 'False'
      onedata['error_flag'] = 'False'

      for items in value:
        if 'Uncertain' in items:
          onedata['uncertain_flag'] = 'True'
        elif 'Error' in items:
          onedata['error_flag'] = 'True'

      onedata['router_name'] = peerip_router_map[remote_ip][0]
      onedata['local_ip'] = peerip_router_map[remote_ip][1]
      onedata['interconnect_name'] = peerip_router_map[remote_ip][3]
      onedata['region'] = peerip_router_map[remote_ip][4]
      onedata['project_id'] = peerip_router_map[remote_ip][5]
      onedata['attachment_name'] = peerip_router_map[remote_ip][6]
      bgpdata[key] = onedata

    op.put(flags.BGP_FLAP_LIST, json.dumps(bgpdata))

    if len(router_logs) > 0:
      reason = '\n'
      if len(err_router_logs) == 0:
        # process BGP flaps with time duration less than graceful restart timer.
        if len(bgpdata) != 0:
          for item in bgpdata.values():
            if item['uncertain_flag'] != 'True':
              continue

            flap_details = '\n\t\tBGP flap details:'
            for oneflap in item['events']:
              flap_details = flap_details + '\n\t\t' + ','.join(oneflap)
            flap_details += '\n'

            reason += op.prep_msg(op.UNCERTAIN_REASON,
                                  router_id=item['router_id'],
                                  local_ip=item['local_ip'],
                                  remote_ip=item['remote_ip'],
                                  router_name=item['router_name'],
                                  attachment=item['attachment_name'],
                                  project_id=item['project_id'],
                                  flap_details=flap_details)

        op.add_uncertain(project,
                         reason=op.prep_msg(op.UNCERTAIN_REASON_ALT1,
                                            project_id=project.id,
                                            timer=GRACEFUL_RESTART_TIMER,
                                            reason=reason),
                         remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))

      else:
        # process BGP flaps with time duration longer than graceful restart timer.
        if len(bgpdata) != 0:
          for item in bgpdata.values():
            if item['error_flag'] != 'True':
              continue

            flap_details = '\n\t\tBGP flap details:'
            for oneflap in item['events']:
              flap_details = flap_details + '\n\t\t' + ','.join(oneflap)
            flap_details += '\n'

            reason += op.prep_msg(op.FAILURE_REASON,
                                  router_id=item['router_id'],
                                  local_ip=item['local_ip'],
                                  remote_ip=item['remote_ip'],
                                  router_name=item['router_name'],
                                  attachment=item['attachment_name'],
                                  project_id=item['project_id'],
                                  flap_details=flap_details)

        example_query = """ \n\nExample query:
            resource.type="gce_router"
            "Maintenance of router task" OR ("came up" OR "went down")
            resource.labels.region="<region>"
            r.esource.labels.router_id="<router_id>"
            """

        op.add_failed(project,
                      reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                         project_id=project.id,
                                         timer=GRACEFUL_RESTART_TIMER,
                                         reason=reason),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              timer=GRACEFUL_RESTART_TIMER,
                                              example_query=example_query))
        return
    else:
      op.add_ok(project,
                reason=op.prep_msg(op.SUCCESS_REASON,
                                   region=op.get(flags.REGION),
                                   project_id=project.id))


class BgpDownFlapEnd(runbook.EndStep):
  """Concludes the diagnostics process.

  The following are considered error and need further debugging:

  1> BGP down events found without interconnect maintenance
  2> BGP flaps with duration over graceful restart timer
  3> BGP flaps with duration less than graceful restart timer but no Cloud Router maintenance event

  Please contact GCP support for further debugging.

  """

  def execute(self):
    """Finalizing connectivity diagnostics."""
    op.info('If any further debugging is needed, '
            'consider please contact GCP support for further troubleshooting')
