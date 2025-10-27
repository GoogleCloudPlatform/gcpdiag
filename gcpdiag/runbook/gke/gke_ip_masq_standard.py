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
"""This runbook will analyze symptoms for IP Masquerading issues on GKE Cluster."""

import ipaddress
from datetime import datetime

from gcpdiag import runbook
from gcpdiag.queries import crm, gke, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gke import flags


class GkeIpMasqStandard(runbook.DiagnosticTree):
  """This runbook will analyze symptoms for IP Masquerading issues on GKE Cluster.

  It examines the following:

  - Are there any traffic logs to destination IP?
  - Is ip-masq-agent DaemonSet in kube-system namespace?
  - Is ip-masq-agent Configmap in kube-system namespace?
  - Is GKE node IP and Pod IP are under nonMasquerade CIDR?
  - Is Destination IP is under are under nonMasquerade CIDR?
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.SRC_IP: {
          'type': ipaddress.IPv4Address,
          'help': 'The source IP from where connection is generated',
      },
      flags.DEST_IP: {
          'type':
              ipaddress.IPv4Address,
          'help':
              'The Destination IP is where the request is sending (Example : 8.8.8.8)',
          'required':
              True
      },
      flags.POD_IP: {
          'type':
              str,
          'help':
              'GKE Pod IP address or pod address range(Example 192.168.1.0/24)',
      },
      flags.NAME: {
          'type':
              str,
          'help':
              'The name of the GKE cluster, to limit search only for this cluster',
          'required':
              False,
          'deprecated':
              True,
          'new_parameter':
              'gke_cluster_name',
      },
      flags.GKE_CLUSTER_NAME: {
          'type':
              str,
          'help':
              'The name of the GKE cluster, to limit search only for this cluster',
      },
      flags.LOCATION: {
          'type': str,
          'help': 'The zone or region of the GKE cluster',
      },
      flags.GKE_NODE_IP: {
          'type':
              str,
          'help':
              'GKE Node IP address or address range/CIDR (Example 192.168.1.0/24)'
      },
      flags.START_TIME: {
          'type': datetime,
          'help': 'Start time of the issue',
      },
      flags.END_TIME: {
          'type': datetime,
          'help': 'End time of the issue',
      }
  }

  def legacy_parameter_handler(self, parameters):
    if flags.NAME in parameters:
      parameters[flags.GKE_CLUSTER_NAME] = parameters.pop(flags.NAME)

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    # start = StandardIpMasqStart()
    start = GkeIpMasqStandardStart()
    self.add_start(start)
    custom = Nodeproblem()
    self.add_step(parent=start, child=custom)
    check_daemon_set_present = CheckDaemonSet()
    self.add_step(parent=start, child=check_daemon_set_present)
    check_config_map_present = CheckConfigMap()
    self.add_step(parent=check_daemon_set_present,
                  child=check_config_map_present)
    check_pod_ip = CheckPodIP()
    self.add_step(parent=check_config_map_present, child=check_pod_ip)
    check_node_ip = CheckNodeIP()
    self.add_step(parent=check_pod_ip, child=check_node_ip)
    check_destination_ip = CheckDestinationIP()
    self.add_step(parent=check_node_ip, child=check_destination_ip)
    self.add_end(GkeIpMasqStandardEnd())


class GkeIpMasqStandardStart(runbook.StartStep):
  """Check if the project ID, GKE cluster and its location is valid.

  Based on information provided would direct toward further troubleshooting.
  """

  def execute(self):
    """Lets check the provided parameters."""
    #     # skip if logging is disabled
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    # check if there are clusters in the project
    clusters = gke.get_clusters(op.get_context())

    # following checks are necessary, depending on what input is provided:
    # - no input, get all clusters available
    # - just cluster name is provided, check if there's a cluster with that name
    # - just location is provided, check if there are clusters at that location
    # - cluster name and location are provided, check if there's that cluster at that location
    cluster_name = op.get(flags.GKE_CLUSTER_NAME)
    cluster_location = op.get(flags.LOCATION)
    found_cluster = False
    found_cluster_with_location = False
    found_clusters_at_location = False
    if cluster_name and cluster_location:
      for cluster in clusters.values():
        if cluster_name == str(cluster).rsplit('/', maxsplit=1)[-1] \
          and cluster_location == str(cluster).split('/')[-3]:
          found_cluster_with_location = True
          op.add_ok(
              project_path,
              reason=(
                  'Cluster with the name {} on {} exist in project {}').format(
                      cluster_name, cluster_location, project))
          break
    elif cluster_name:
      for cluster in clusters.values():
        if cluster_name == str(cluster).rsplit('/', maxsplit=1)[-1]:
          found_cluster = True
          op.add_ok(project_path,
                    reason=('Cluster with name {} exist in project {}').format(
                        cluster_name, project))
          break
    elif cluster_location:
      for cluster in clusters.values():
        if cluster_location == str(cluster).split('/')[-3]:
          found_clusters_at_location = True
          op.add_uncertain(
              project_path,
              reason=
              ('There are clusters found on {} location. Please add cluster name to limit search'
              ).format(cluster_location))
          break
    if not found_cluster_with_location and cluster_location and cluster_name:
      op.add_skipped(
          project_path,
          reason=('Cluster with the name {} in {} does not exist in project {}'
                 ).format(cluster_name, cluster_location, project))
    # next check includes found_cluster_with_location because we found a cluster at a particular
    # location thus we cannot skip these checks
    elif not found_cluster and not found_cluster_with_location and cluster_name:
      op.add_skipped(
          project_path,
          reason=(
              'Cluster with the name {} does not exist in project {}').format(
                  cluster_name, project))
    elif not found_clusters_at_location and not found_cluster_with_location and cluster_location:
      op.add_skipped(
          project_path,
          reason=('No clusters found at location {} in project {}').format(
              cluster_location, project))


class Nodeproblem(runbook.Step):
  """This will confirm if there is any VPC flow logs to destination IP.

  This will either rule out ip-masq issue or points to ip-mas-agent issue.
  """
  template = 'ipmasq_standard::Nodeproblem'

  def execute(self):
    """Are you seeing issue from GKE NODE as well?"""

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=f'''"{op.get(flags.DEST_IP)}" OR "{op.get(flags.SRC_IP)}"''',
        start_time=op.get(flags.END_TIME),
        end_time=datetime.now())

    if log_entries:
      op.add_ok(project_path, reason=op.prep_msg(op.SUCCESS_REASON))
    else:
      op.add_failed(project_path,
                    reason=op.prep_msg(op.FAILURE_REASON),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class CheckDaemonSet(runbook.Step):
  """ On GKE for ip-masq can be deployed or automatically in cluster.

  This step will verify if Daemon set present?
  """
  template = 'ipmasq_standard::daemon'

  def execute(self):
    """Lets check if Daemon set present.."""

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)
    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    op.add_uncertain(project_path,
                     reason=op.prep_msg(op.UNCERTAIN_REASON),
                     remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class CheckConfigMap(runbook.Step):
  """ This will confirm config map is present as that llow user to make changes on ip-agent.

  This will check if config map is present ?
  """
  template = 'ipmasq_standard::configmap'

  def execute(self):
    """Lets confirm if config map  is configure."""

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    op.add_uncertain(project_path,
                     reason=op.prep_msg(op.UNCERTAIN_REASON),
                     remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class CheckPodIP(runbook.Step):
  """ GKE preserves the Pod IP addresses sent to destinations in the nonMasqueradeCIDRs list.

  This will confirm if pod IP is present on the list.
  """
  template = 'ipmasq_standard::pod'

  def execute(self):
    """Lets check pod ip present.."""

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    op.add_uncertain(project_path,
                     reason=op.prep_msg(op.UNCERTAIN_REASON),
                     remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class CheckNodeIP(runbook.Step):
  """ When Node IP is present under non-masquerade list, it will allow node IP to not get natted .

  This will check node IP address is present default non-masquerade destinations.
  """
  template = 'ipmasq_standard::node'

  def execute(self):
    '''Lets check node IP is present under non-masq cidr.'''

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    op.add_uncertain(project_path,
                     reason=op.prep_msg(op.UNCERTAIN_REASON),
                     remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class CheckDestinationIP(runbook.Step):
  """GKE is expected not to IP masquerade. If needed then it should be added on nonMasqueradeCIDRs.

  This will confirm if pod IP is present on the list.
  """
  template = 'ipmasq_standard::destination'

  def execute(self):
    '''Lets check if pod ip address is present.'''

    project = op.get(flags.PROJECT_ID)
    project_path = crm.get_project(project)

    op.add_uncertain(project_path,
                     reason=op.prep_msg(op.UNCERTAIN_REASON),
                     remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))


class GkeIpMasqStandardEnd(runbook.EndStep):
  """Concludes the the diagnostics process.

  If connectivity issue presits from pod, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalize connectivity diagnostics."""

    op.info(
        message=
        'If all check passed consider please contact support for further troubleshooting'
    )
