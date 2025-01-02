# Copyright 2024 Google LLC
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
"""GKE Node Bootstrapping runbook"""

# input would be a location (zone for a node) and a node name
# if a node name cannot be provided, then a nodepool name should be provided. With the nodepool
# name and location (zone or region for a nodepool), we can check if there are instances.insert
# errors.
# if a node name and location is provided, we can check Node Registration Checker logs
#
# logic used for the node registration checker:
# - check if it's a GKE node, skip if it isn't
# - check if the node exists and 10 minutes passed since instance was started, to make sure there's
#   enough time for Node Registration Checker to run
# - check if node's service account has logging permissions, otherwise we don't have logs to look
#   into
# - check if node exists and it's running
#   - check if START_TIME_UTC is before node boot, so we can capture the boot time logs
#   - if yes, check for Node Registration Checker logs:
#     - if "Node ready and registered." found, all good, return OK result
#     - else if "Completed running Node Registration Checker" found, then it's a failure and
#       provide the summary.
#     - check if multiple "Completed running Node Registration Checker" messages are found for the
#       same node name, this means it's in a repair loop
#   - else (the node is not running) check if there are any logs for instance id and location
#     provided, if there are no logs, this means either the node didn't exist in the time range
#     provided, or the input is incorrect (node/location pair)
#   - else if "Node ready and registered." found for node name, then it registered at some point in
#     the past (limited to search interval)
#   - else check for instance name and see if Node Registration Checker finished running and
#     provide output
#   - else fail because Node Registration Checker didn't complete

from datetime import datetime, timedelta, timezone

import googleapiclient.errors

from gcpdiag import models, runbook
from gcpdiag.queries import crm, gce, gke, iam, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags

TOKEN_NRC_START = '** Here is a summary of the checks performed: **'


def get_node_instance(project, location, node):
  # check if node exists, location here is zone, because it's a single node
  try:
    node_vm = gce.get_instance(project, location, node)
  except googleapiclient.errors.HttpError:
    return None
  else:
    return node_vm


def local_realtime_query(filter_str):
  result = logs.realtime_query(project_id=op.get(flags.PROJECT_ID),
                               start_time_utc=op.get(flags.START_TIME_UTC),
                               end_time_utc=op.get(flags.END_TIME_UTC),
                               filter_str=filter_str)
  return result


def get_nrc_summary(node, location):
  filter_str = [
      f'labels."compute.googleapis.com/resource_name"="{node}"',
      'resource.type="gce_instance"', f'resource.labels.zone="{location}"',
      'log_id("serialconsole.googleapis.com/serial_port_1_output")',
      'textPayload:"node-registration-checker.sh"'
  ]
  filter_str = '\n'.join(filter_str)
  log_entries_all = local_realtime_query(filter_str)

  found = False
  nrc_summary = []
  for log_entry in log_entries_all:
    if TOKEN_NRC_START in log_entry['textPayload']:
      # found match for the summary and taking its index position
      # ncr_start_pos = log_entries_all.index(log_entry)
      found = True
    if found:
      nrc_summary.append(log_entry['textPayload'])
    if '** Completed running Node Registration Checker **' in log_entry[
        'textPayload']:
      break

  return nrc_summary


class NodeBootstrapping(runbook.DiagnosticTree):
  """Analyses issues experienced when adding nodes to your GKE Standard cluster.

  This runbook requires at least
  - location and node parameters. Location here is the zone where the node is running,
  for example us-central1-c.
  - location, nodepool and cluster name parameters to be provided. Location is zone or region for
  a nodepool, if the cluster is a regional cluster, then location for a nodepool will be the
  cluster region. For example a region could be us-central1.

  If a location/node pair is provided, the runbook will check the Node Registration Checker output
  for the given location/node pair.

  If a location, nodepool and GKE cluster name parameters are provided, the runbook will check for
  any errors that might have occurred when the instances.insert method was invoked for the given
  parameters.
  """
  # Specify parameters common to all steps in the diagnostic tree class.
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The ID of the project hosting the GKE Cluster',
          'required': True
      },
      flags.LOCATION: {
          'type':
              str,
          'help':
              'The location where the node or nodepool is. For a node, location will be the zone \
where the node is running (i.e. us-central1-c). For a nodepool, this can be the zone or the \
region (i.e. us-central1) where the nodepool is configured',
          'required':
              True
      },
      flags.NODE: {
          'type':
              str,
          'help':
              'The node name that is failing to register (if available). If node name is not \
available, please provide the nodepool name where nodes aren\'t registering',
          'required':
              False
      },
      flags.NODEPOOL: {
          'type':
              str,
          'help':
              'The nodepool name where nodes aren\'t registering, if a node name is not \
availalbe',
          'required':
              False
      },
      flags.NAME: {
          'type':
              str,
          'help':
              'The GKE cluster name. When providing nodepool name, please provide the GKE cluster \
name as well to be able to properly filter events in the logging query.',
          'required':
              False
      },
      flags.START_TIME_UTC: {
          'type':
              datetime,
          'help':
              'The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ'
      },
      flags.END_TIME_UTC: {
          'type':
              datetime,
          'help':
              'The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ'
      }
  }

  def build_tree(self):
    start = NodeBootstrappingStart()
    node_insert_ok = NodeInsertCheck()
    node_reg_ok = NodeRegistrationSuccess()
    end = NodeBootstrappingEnd()

    self.add_start(step=start)
    self.add_step(parent=start, child=node_insert_ok)
    self.add_step(parent=node_insert_ok, child=node_reg_ok)
    self.add_end(step=end)


class NodeBootstrappingStart(runbook.StartStep):
  """Initiates diagnostics for Node Bootstrapping.

  Check
  - if there are GKE clusters in the project
  - if the instance provided is a GKE node
  - if serial logs are enabled
  - if there are any logs for the provided inputs
  """

  def execute(self):
    """
    Check the provided parameters.
    """
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)

    # check if there are clusters in the project
    if name:
      clusters = gke.get_clusters(
          models.Context(project_id=project, resources=[name]))
      if not clusters:
        op.add_skipped(
            project_path,
            reason=f'No {name} GKE cluster found in project {project}')
        return
    else:
      clusters = gke.get_clusters(op.context)
      if not clusters:
        op.add_skipped(
            project_path,
            reason=('No GKE clusters found in project {}').format(project))
        return

    # check if node exists
    if node:
      node_vm = get_node_instance(project, location, node)

      if node_vm:
        if not node_vm.is_gke_node():
          op.add_skipped(
              project_path,
              reason=
              (f'Instance {node} in location {location} does not appear to be a GKE node'
              ))
          return
        elif not node_vm.is_serial_port_logging_enabled():
          op.add_skipped(
              project_path,
              reason=
              (f'Instance {node} in location {location} does not have Serial Logs enabled, please '
               'enable serial logs for easier troubleshooting.'))
          return

      # fail if Audit Log does not have any log entries for the input provided, meaning there could
      # have been an input error
      filter_str = [
          'log_id("cloudaudit.googleapis.com/activity")',
          f'resource.labels.zone="{location}"',
          f'protoPayload.resourceName:"{node}"'
      ]
      filter_str = '\n'.join(filter_str)

      log_entries = local_realtime_query(filter_str)

      if not log_entries:
        op.add_skipped(
            project_path,
            reason=
            (f'There are no log entries for the provided node {node} and location '
             f'{location} in the provided time range '
             f'{start_time_utc} - {end_time_utc}.\n'
             'Please make sure the node/location pair is correct and it was booted '
             'in the time range provided, then try again this runbook.'))
        return


class NodeInsertCheck(runbook.Step):
  """Check for any errors during instances.insert method"""

  template = 'nodebootstrapping::node_insert_check'
  MAX_GKE_NAME_LENGTH = 16

  def execute(self):
    """
    Check for any errors during instances.insert method for the given location (region or zone)
    and nodepool pair.
    """
    project = op.get(flags.PROJECT_ID)
    location = op.get(flags.LOCATION)
    nodepool = op.get(flags.NODEPOOL)
    node = op.get(flags.NODE)
    name = op.get(flags.NAME)
    project_path = crm.get_project(project)
    start_time_utc = op.get(flags.START_TIME_UTC)
    end_time_utc = op.get(flags.END_TIME_UTC)

    if nodepool and name:
      if not node:
        # the gke instance name will have a max of 16 characters from the nodepool name
        # and max 16 characters from the GKE cluster name
        filter_str = [
            'log_id("cloudaudit.googleapis.com/activity")',
            'protoPayload.methodName="v1.compute.instances.insert"',
            'resource.type="gce_instance"', 'severity=ERROR',
            f'protoPayload.resourceName:"{location}"',
            f'protoPayload.resourceName:"{name[:self.MAX_GKE_NAME_LENGTH]}"',
            f'protoPayload.resourceName:"{nodepool[:self.MAX_GKE_NAME_LENGTH]}"'
        ]
        filter_str = '\n'.join(filter_str)

        log_entries = local_realtime_query(filter_str)

        if log_entries:
          nr_errors = len(log_entries)
          for log_entry in log_entries:
            sample_log = log_entry
            sample_log = str(sample_log).replace(', ', '\n')
            break
          op.add_failed(project_path,
                        reason=op.prep_msg(op.FAILURE_REASON,
                                           LOG_ENTRY=sample_log,
                                           NODEPOOL=nodepool,
                                           NAME=name,
                                           LOCATION=location,
                                           NR_ERRORS=nr_errors,
                                           START_TIME_UTC=start_time_utc,
                                           END_TIME_UTC=end_time_utc),
                        remediation=op.prep_msg(op.FAILURE_REMEDIATION))
          return
        else:
          op.add_ok(project_path,
                    reason=op.prep_msg(op.SUCCESS_REASON,
                                       START_TIME_UTC=start_time_utc,
                                       END_TIME_UTC=end_time_utc,
                                       NODEPOOL=nodepool,
                                       NAME=name,
                                       LOCATION=location))
          return
      else:
        op.add_skipped(
            project_path,
            reason=
            ('Node parameter provided together with nodepool parameter, proceeding with Node '
             'Registration Checkout output verification ...'))
    else:
      op.add_skipped(
          project_path,
          reason=
          ('No nodepool or GKE cluster name provided, skipping this step ... \n'
           'Please provide nodepool name (-p nodepool=<nodepoolname>) and GKE cluster name '
           '(-p name=<gke-cluster-name>) if you see issues with nodes not appearing in the '
           'nodepool.'))
      return


class NodeRegistrationSuccess(runbook.Step):
  """Verify Node Registration Checker output"""
  template = 'nodebootstrapping::node_registration_checker'
  NODE_BOOT_NCR_READY_MIN_TIME = 7

  def execute(self):
    """
    Verify if Node Registration Checker completed running.

    If the node was successfully registered, provide log entry proving successful registration
    If the node wasn't registered successfully, provide Node Registration Checker summary to
    understand why.
    """
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    location = op.get(flags.LOCATION)
    node = op.get(flags.NODE)

    if node:

      # default filter that is used in all log searches
      default_filter = [
          'resource.type="gce_instance"', f'resource.labels.zone="{location}"',
          'log_id("serialconsole.googleapis.com/serial_port_1_output")',
          'textPayload:"node-registration-checker.sh"'
      ]
      default_filter = '\n'.join(default_filter)
      # get node instance
      node_vm = get_node_instance(project, location, node)

      if node_vm and node_vm.is_running:
        # Check if NODE_BOOT_NCR_READY_MIN_TIME minutes (should be at least 7 minutes) passed since
        # the instance was booted, to make sure there was enough time for Node Registration Checker
        # to finish running
        time_since_creation = datetime.now(
        ) - node_vm.creation_timestamp >= timedelta(
            minutes=self.NODE_BOOT_NCR_READY_MIN_TIME)

        if not time_since_creation:
          op.add_failed(
              project_path,
              reason=
              (f'Instance {node} with instance-id {node_vm.id} in location {location} just booted '
               f'at {node_vm.creation_timestamp}.'),
              remediation=
              (f'Please allow for at least {self.NODE_BOOT_NCR_READY_MIN_TIME} minutes since '
               'starting the instance to allow for Node Registration Checker to finish running.'
              ))
          return

      if node_vm:
        # check node service account has logging write permissions
        iam_policy = iam.get_project_policy(project)
        if not iam_policy.has_role_permissions(
            f'serviceAccount:{node_vm.service_account}',
            'roles/logging.logWriter'):
          op.add_failed(
              project_path,
              reason=
              (f'The service account {node_vm.service_account} for node {node} in location '
               f'{location} does not have "Logs Writer (roles/logging.logWriter)" role '
               'permissions. "Logs Writer" permissions are needed for the Node Registration '
               'Checker\'s output to be written in Cloud Logging, where we can analyse it.'
              ),
              remediation=
              ('Add the minimum permissions required to operate GKE to the Node\'s Service '
               f'Account {node_vm.service_account} following the documentation: '
               'https://cloud.google.com/kubernetes-engine/docs/how-to/hardening-your-cluster'
               '#permissions'))
          return

      # if serial log is enabled, we can check Cloud Logging for node-registration-checker.sh
      # output:
      if node_vm and node_vm.is_running and node_vm.is_serial_port_logging_enabled(
      ):
        # check if START_TIME_UTC is after node's boot time if yes we might not find Node
        # Registration Checker logs, so the user needs to set earlier START_TIME_UTC

        # get the offset-aware datetime instead of offset-naive
        node_start_time = datetime.fromisoformat(str(
            node_vm.creation_timestamp)).replace(tzinfo=timezone.utc)
        if node_start_time < op.get(flags.START_TIME_UTC):
          op.add_failed(
              project_path,
              reason=
              (f'The node {node} in the location {location} booted at {node_start_time} before '
               f'the provided START_TIME_UTC {op.get(flags.START_TIME_UTC)} '
               '(default is 8 hours from now)'),
              remediation=
              ('Please provide the START_TIME_UTC parameter (-p start_time_utc) with a date '
               f'before {node_start_time}, so that the runbook can find the Node Registration '
               'Checker logs for the node'))
          return

        filter_str = [
            f'resource.labels.instance_id="{node_vm.id}"', default_filter,
            'textPayload:"Node ready and registered."'
        ]
        filter_str = '\n'.join(filter_str)

        log_entries_success = local_realtime_query(filter_str)

        if log_entries_success:
          # node registered successfully, we're all good
          sample_log = log_entries_success.pop()
          sample_log = str(sample_log).replace(', ', '\n')
          op.add_ok(project_path,
                    reason=op.prep_msg(op.SUCCESS_REASON,
                                       LOG_ENTRY=sample_log,
                                       NODE=node))

        else:
          # node failed to register, need to find Node Registration Checker summary verify if
          # node-registration-checker.sh finished running
          filter_str = [
              f'resource.labels.instance_id="{node_vm.id}"', default_filter,
              'textPayload:"Completed running Node Registration Checker"'
          ]
          filter_str = '\n'.join(filter_str)

          log_entries_completed = local_realtime_query(filter_str)

          if log_entries_completed:
            # node registration finished running but node didn't register. Get all logs for info
            filter_str = [
                f'resource.labels.instance_id="{node_vm.id}"', default_filter
            ]
            filter_str = '\n'.join(filter_str)
            log_entries_all = local_realtime_query(filter_str)

            # log_entries_all have now all the logs until the final "Completed running Node
            # Registration Checker" message, thus we need to pop messages one by one and go back
            # until the start of the NRC report message "Here is a summary of the checks performed"
            found = False
            nrc_summary = []
            while not found:
              nrc_summary.insert(0, log_entries_all.pop()['textPayload'])
              if TOKEN_NRC_START in nrc_summary[0]:
                found = True

            op.add_failed(project_path,
                          reason=op.prep_msg(op.FAILURE_REASON,
                                             LOG_ENTRIES=nrc_summary,
                                             NODE=node,
                                             LOCATION=location),
                          remediation=op.prep_msg(op.FAILURE_REMEDIATION))
            return

          else:
            # Could not find message that Node Registration Checker finished running for instance
            # id, checking by node name and look for potential repair loop
            filter_str = [
                f'labels."compute.googleapis.com/resource_name"="{node}"',
                default_filter,
                'textPayload:"Completed running Node Registration Checker"'
            ]
            filter_str = '\n'.join(filter_str)

            log_entries_completed = local_realtime_query(filter_str)

            if log_entries_completed:
              # as there is "Completed running Node Registration Checker" log entry but not for
              # current instance_id, this means that the node is in a repair loop. Need to find out
              # the summary taking into account that there could be multiple summaries
              nrc_summary = get_nrc_summary(node, op.get(flags.LOCATION))

              op.add_failed(project_path,
                            reason=op.prep_msg(op.FAILURE_REASON_ALT1,
                                               LOG_ENTRIES=nrc_summary,
                                               NODE=node,
                                               LOCATION=location),
                            remediation=op.prep_msg(op.FAILURE_REMEDIATION))
              return
            else:
              # node is running, but there's no "Completed running Node Registration Checker" log
              # entry in the provided time range
              op.add_failed(project_path,
                            reason=op.prep_msg(
                                op.UNCERTAIN_REASON,
                                NODE=node,
                                LOCATION=location,
                                START_TIME_UTC=op.get(flags.START_TIME_UTC),
                                END_TIME_UTC=op.get(flags.END_TIME_UTC)),
                            remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                                    NODE=node))
              return

      else:
        # node doesn't exist, checking older logs by node name and trying to find if Node
        # Registration Checker completed running at least once
        filter_str = [
            f'labels."compute.googleapis.com/resource_name"="{node}"',
            default_filter, 'textPayload:"Node ready and registered."'
        ]
        filter_str = '\n'.join(filter_str)

        log_entries_success = local_realtime_query(filter_str)

        if log_entries_success:
          # node isn't running now, but it registered successfully in the past
          sample_log = log_entries_success.pop()
          sample_log = str(sample_log).replace(', ', '\n')
          op.add_ok(project_path,
                    reason=op.prep_msg(op.SUCCESS_REASON_ALT1,
                                       LOG_ENTRY=sample_log,
                                       NODE=node))
        else:
          filter_str = [
              f'labels."compute.googleapis.com/resource_name"="{node}"',
              default_filter,
              'textPayload:"Completed running Node Registration Checker"'
          ]
          filter_str = '\n'.join(filter_str)

          log_entries_completed = local_realtime_query(filter_str)

          if log_entries_completed:
            # Node Registration Checker completed running.  Need to find out the summary, taking
            # into account that there could be multiple summaries
            nrc_summary = get_nrc_summary(node, op.get(flags.LOCATION))

            op.add_failed(project_path,
                          reason=op.prep_msg(op.FAILURE_REASON_ALT2,
                                             LOG_ENTRIES=nrc_summary,
                                             NODE=node,
                                             LOCATION=location),
                          remediation=op.prep_msg(op.FAILURE_REMEDIATION))
            return

          else:
            # node is not running and Node Registration Checker did not complete running. Most
            # probably the node was deleted before Node Registration Checker could finish running.
            op.add_failed(project_path,
                          reason=op.prep_msg(op.FAILURE_REASON_ALT3,
                                             NODE=node,
                                             LOCATION=location),
                          remediation=op.prep_msg(op.FAILURE_REMEDIATION_ALT3))
            return
    else:
      op.add_skipped(
          project_path,
          reason=
          ('No node name provided, skipping this step ...\n'
           'Please provide node name (-p node=<nodename>) if the node appears in the nodepool, '
           'but fails registration.\n'))


class NodeBootstrappingEnd(runbook.EndStep):
  """Finalizes the diagnostics process for `GKE Node Bootstrapping`.

  This step prompts the user to confirm satisfaction with the analysis performed for
  `GKE Node Bootstrapping`.

  Depending on the user's response, it may conclude the runbook execution or trigger additional
  steps, such as generating a report of the findings.
  """

  def execute(self):
    """Finalizing `GKE Node Bootstrapping` diagnostics..."""
    response = op.prompt(
        kind=op.CONFIRMATION,
        message='Are you satisfied with the `GKE Node Bootstrapping` analysis?')
    if response == op.NO:
      op.info(message=op.END_MESSAGE)
