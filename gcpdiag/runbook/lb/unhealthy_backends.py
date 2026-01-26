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
"""Module containing steps to analyze Health Check issues."""

import re
import urllib.parse
from datetime import datetime, timedelta
from itertools import groupby
from typing import List, Optional

import googleapiclient.errors
from boltons.iterutils import get_path

from gcpdiag import config, runbook
from gcpdiag.queries import apis, crm, gce, lb, logs
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.lb import flags


class UnhealthyBackends(runbook.DiagnosticTree):
  """Load Balancer Unhealthy Backends Analyzer.

  This runbook helps investigate why backends in a load balancer are unhealthy.
  It confirms and summarizes the current health status of the backends, aiding
  in identifying any unhealthy instances.

  Key Investigation Areas:

  - Firewalls:
      - Verifies if firewall rules are properly configured to allow health check
      traffic.
  - Port Configuration:
      - Checks if health check sends probe requests to the different port than
      serving port. This may be intentional or a potential configuration error,
      and the runbook will provide guidance on the implications.
  - Protocol Configuration:
      - Checks if health check uses the same protocol as backend service. This
      may be intentional or a potential configuration error, and the runbook
      will provide guidance on the implications.
  - Logging:
      - Checks if health check logging is enabled to aid in troubleshooting.
  - Health Check Logs (if enabled):
      - Analyzes the latest health check logs to identify the specific reasons
      for backend unhealthiness:
          - Timeouts: Identifies if the backend is timing out and provides
          potential causes and remediation steps.
          - Unhealthy: Indicates that the backend is reachable but doesn't meet
          the health check's criteria. It provides guidance on the expected
          health check behavior and suggests configuration checks.
          - Unknown: Explains the potential reasons for the "UNKNOWN" health
          state and suggests actions like adjusting timeouts or checking for
          Google Cloud outages.
  - Past Health Check Success:
      - Checks if the health check has worked successfully in the past to
      determine if the issue is recent or ongoing.
  - VM Performance:
      - Checks if the instances performance is degraded - disks, memory and cpu
      utilization are being checked.
  """

  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True,
      },
      flags.BACKEND_SERVICE_NAME: {
          'type': str,
          'help':
              ('The name of the backend service that you want to investigate'),
          'required': True,
      },
      flags.REGION: {
          'type': str,
          'help':
              ('The region configured for the load balancer (backend service).'
               ' If not provided, the backend service is assumed to be global.'
              ),
          'required': False,
      },
  }

  def build_tree(self):
    """Fetches primary resources and builds the diagnostic tree."""
    project_id = op.get(flags.PROJECT_ID)
    backend_service_name = op.get(flags.BACKEND_SERVICE_NAME)
    region = op.get(flags.REGION, 'global')

    # The start step is always added. Its execute method will determine the
    # initial message based on the objects it receives.
    start = UnhealthyBackendsStart()
    start.project_id = project_id
    start.backend_service_name = backend_service_name
    start.region = region
    self.add_start(start)
    logging_check = VerifyHealthCheckLoggingEnabled()
    port_check = ValidateBackendServicePortConfiguration()
    protocol_check = ValidateBackendServiceProtocolConfiguration()
    firewall_check = VerifyFirewallRules()
    vm_performance_check = CheckVmPerformance()
    self.add_step(parent=start, child=logging_check)
    self.add_step(parent=start, child=port_check)
    self.add_step(parent=start, child=protocol_check)
    self.add_step(parent=start, child=firewall_check)
    self.add_step(parent=start, child=vm_performance_check)
    self.add_end(UnhealthyBackendsEnd())
    # Pre-flight checks before fetching resources
    if not apis.is_enabled(project_id, 'compute'):
      start.error_message = (
          'Compute Engine API is not enabled. Please enable it and try again.')
      return

    # Fetch all primary resources once to avoid redundant API calls
    try:
      backend_service = lb.get_backend_service(project_id, backend_service_name,
                                               region)
    except googleapiclient.errors.HttpError:
      # If the backend service doesn't exist, we can't proceed.
      # The start step will report this and the runbook will end.
      start.error_message = (
          f'Backend service {backend_service_name} does not exist in scope'
          f' {region} or project {project_id}')
      return
    start.backend_service = backend_service

    if not backend_service.health_check:
      start.error_message = (
          f'Backend service {backend_service_name} does not have a health check'
          f' configured in scope {region} or project {project_id}')
      return

    health_check = gce.get_health_check(project_id,
                                        backend_service.health_check,
                                        backend_service.health_check_region)
    start.health_check = health_check

    backend_health_statuses = lb.get_backend_service_health(
        op.get_context(), backend_service_name, region)
    start.backend_health_statuses = backend_health_statuses

    if not backend_health_statuses:
      # Start step will see this list is empty and report no backends.
      return

    # If we got this far, we have all necessary objects. Now, build the
    # rest of the tree and pass the fetched objects to each step.

    logging_check.project_id = project_id
    logging_check.region = region
    logging_check.backend_service_name = backend_service_name
    logging_check.backend_service = backend_service
    logging_check.health_check = health_check
    logging_check.backend_health_statuses = backend_health_statuses

    port_check.project_id = project_id
    port_check.region = region
    port_check.backend_service_name = backend_service_name
    port_check.backend_service = backend_service
    port_check.health_check = health_check

    protocol_check.project_id = project_id
    protocol_check.region = region
    protocol_check.backend_service_name = backend_service_name
    protocol_check.backend_service = backend_service
    protocol_check.health_check = health_check

    firewall_check.project_id = project_id
    firewall_check.region = region
    firewall_check.backend_service_name = backend_service_name
    firewall_check.backend_service = backend_service

    vm_performance_check.project_id = project_id
    vm_performance_check.region = region
    vm_performance_check.backend_service_name = backend_service_name
    vm_performance_check.backend_health_statuses = backend_health_statuses


class UnhealthyBackendsStart(runbook.StartStep):
  """Start step for Unhealthy Backends runbook."""

  template = 'unhealthy_backends::confirmation'
  project_id: str
  backend_service_name: str
  region: str

  # Pre-fetched objects from the parent DiagnosticTree
  backend_service: Optional[lb.BackendServices] = None
  health_check: Optional[gce.HealthCheck] = None
  backend_health_statuses: Optional[List[lb.BackendHealth]] = None

  error_message: str = ''

  @property
  def name(self):
    return (f'Analyze unhealthy backends for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks the health of a specified load balancer's backends."""
    proj = crm.get_project(self.project_id)

    if self.error_message:
      op.add_skipped(proj, reason=self.error_message)
      return

    if not self.backend_service:
      op.add_skipped(
          proj,
          reason=(f'Backend service {self.backend_service_name} does not'
                  f' exist in scope {self.region} or project'
                  f' {self.project_id}'),
      )
      return

    if not self.backend_health_statuses:
      op.add_skipped(
          proj,
          reason=(f'Backend service {self.backend_service_name} does not'
                  f' have any backends in scope {self.region} or'
                  f' project {self.project_id}'),
      )
      return

    unhealthy_backends = [
        backend for backend in self.backend_health_statuses
        if backend.health_state == 'UNHEALTHY'
    ]

    backend_health_statuses_per_group = {
        k: list(v)
        for k, v in groupby(self.backend_health_statuses, key=lambda x: x.group)
    }

    if unhealthy_backends:
      detailed_reason = ''
      for group, backends_in_group in backend_health_statuses_per_group.items():
        unhealthy_count = sum(
            1 for x in backends_in_group if x.health_state == 'UNHEALTHY')
        detailed_reason += (
            f'Group {group} has {unhealthy_count}/{len(backends_in_group)} '
            'unhealthy backends\n')
      op.add_failed(
          resource=self.backend_service,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              name=self.backend_service_name,
              region=self.region,
              detailed_reason=detailed_reason,
              hc_name=self.health_check.name,
              success_criteria=get_health_check_success_criteria(
                  self.health_check),
              timing_and_threshold=_get_timing_and_threshold_info(
                  self.health_check)),
          remediation='',
      )
    else:
      if not self.health_check.is_log_enabled:
        op.add_uncertain(
            resource=self.backend_service,
            reason=op.prep_msg(
                op.UNCERTAIN_REASON,
                name=self.backend_service_name,
                region=self.region,
            ),
        )
        return

      # Check for past unhealthy logs
      all_groups = {status.group for status in self.backend_health_statuses}
      group_filters = []
      group_metadata = {}
      detailed_reason = ''
      past_issue_found = False

      for group in all_groups:
        m = re.search(r'/(?:regions|zones)/([^/?]+)/([^/?]+)/([^/?]+)', group)
        if not m:
          continue

        location = m.group(1)
        resource_type = m.group(2)
        resource_name = m.group(3)

        if resource_type == 'instanceGroups':
          # Construct individual filter part and store metadata for mapping logs back to group URL
          filter_part = (
              f'(resource.type="gce_instance_group" AND '
              f'resource.labels.instance_group_name="{resource_name}" AND '
              f'resource.labels.location=~"{location}")')
          group_filters.append(filter_part)
          group_metadata[('gce_instance_group', resource_name,
                          location)] = group
        elif resource_type == 'networkEndpointGroups':
          neg = _get_zonal_network_endpoint_group(self.project_id, location,
                                                  resource_name)
          if neg:
            filter_part = (
                f'(resource.type="gce_network_endpoint_group" AND '
                f'resource.labels.network_endpoint_group_id="{neg.id}" AND '
                f'resource.labels.zone="{location}")')
            group_filters.append(filter_part)
            group_metadata[('gce_network_endpoint_group', neg.id,
                            location)] = group

      if group_filters:
        # Aggregate filters into a single query
        aggregated_filter = """log_name="projects/{}/logs/compute.googleapis.com%2Fhealthchecks"
                            (jsonPayload.healthCheckProbeResult.healthState="UNHEALTHY" OR
                             jsonPayload.healthCheckProbeResult.previousHealthState="UNHEALTHY")
                            AND ({})
                            """.format(self.project_id,
                                       ' OR '.join(group_filters))

        log_entries = logs.realtime_query(
            project_id=self.project_id,
            filter_str=aggregated_filter,
            start_time=datetime.now() - timedelta(minutes=10),
            end_time=datetime.now(),
            disable_paging=True,
        )

        if log_entries:
          past_issue_found = True
          affected_groups = set()
          for entry in log_entries:
            rtype = get_path(entry, ('resource', 'type'))
            labels = get_path(entry, ('resource', 'labels'), {})
            # Normalize location and name for metadata mapping
            loc = labels.get('location') or labels.get('zone')
            name = labels.get('instance_group_name') or labels.get(
                'network_endpoint_group_id')
            group_url = group_metadata.get((rtype, name, loc))
            # Fallback for regional MIGs where logs report the zone
            if not group_url and loc:
              parts = loc.rsplit('-', 1)
              if len(parts) == 2:
                region = parts[0]
                group_url = group_metadata.get((rtype, name, region))

            if group_url:
              affected_groups.add(group_url)

          detailed_reason = ''.join([
              f'Group {g} had unhealthy backends in the last 10 minutes.\n'
              for g in sorted(affected_groups)
          ])

      if past_issue_found:
        op.add_failed(
            resource=self.backend_service,
            reason=op.prep_msg(
                op.FAILURE_REASON_ALT1,
                name=self.backend_service_name,
                region=self.region,
                detailed_reason=detailed_reason,
            ),
            remediation='',
        )
      else:
        op.add_ok(
            resource=self.backend_service,
            reason=op.prep_msg(
                op.SUCCESS_REASON,
                name=self.backend_service_name,
                region=self.region,
            ),
        )


class CheckVmPerformance(runbook.CompositeStep):
  """Checks if the instances performance is degraded."""

  template = 'unhealthy_backends::vm_performance'
  project_id: str
  backend_service_name: str
  region: str
  backend_health_statuses: List[lb.BackendHealth]

  @property
  def name(self):
    return (f'Check VMs performance for unhealthy backends in backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if the VM performance is degraded.

    In this step one unhealthy instance from each group is analyzed - disks,
    memory and cpu utilization are being checked.
    """
    instances_to_analyze_by_group = {}

    for status in sorted(
        self.backend_health_statuses,
        key=lambda obj: obj.instance):  # sorting to make testing predictable
      if status.health_state == 'UNHEALTHY':
        instances_to_analyze_by_group[status.group] = status.instance

    for group, instance in instances_to_analyze_by_group.items():
      m = re.search(r'projects/([^/?]+)/zones/([^/?]+)/instances/([^/?]+)',
                    instance)
      if not m:
        raise RuntimeError(
            "Can't determine project, zone or instance name from self links"
            f' {group}')

      project_id = m.group(1)
      zone = m.group(2)
      instance_name = m.group(3)
      instance_object = gce.get_instance(project_id=project_id,
                                         zone=zone,
                                         instance_name=instance_name)
      if not instance_object:
        op.add_skipped(
            None,
            reason=
            f'VM instance {instance_name} not found in project {project_id} zone {zone}'
        )

      mem_check = gce_gs.HighVmMemoryUtilization()
      mem_check.vm = instance_object
      disk_check = gce_gs.HighVmDiskUtilization()
      disk_check.vm = instance_object
      cpu_check = gce_gs.HighVmCpuUtilization()
      cpu_check.vm = instance_object

      self.add_child(mem_check)
      self.add_child(disk_check)
      self.add_child(cpu_check)


class VerifyFirewallRules(runbook.Step):
  """Checks if firewall rules are configured correctly."""

  template = 'unhealthy_backends::firewall_rules'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices

  @property
  def name(self):
    return (f'Verify firewall rules allow health checks for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if firewall rules are configured correctly."""
    if not apis.is_enabled(self.project_id, 'recommender'):
      op.add_skipped(
          crm.get_project(self.project_id),
          reason=(
              'Checking firewall rules requires Recommender API to be enabled'),
      )
      return

    used_by_refs = self.backend_service.used_by_refs
    insights = lb.get_lb_insights_for_a_project(self.project_id, self.region)
    for insight in insights:
      if insight.is_firewall_rule_insight and insight.details.get(
          'loadBalancerUri'):
        # network load balancers (backend service is central resource):
        if insight.details.get('loadBalancerUri').endswith(
            self.backend_service.full_path):
          op.add_metadata('insightDetail', insight.details)
          op.add_failed(
              resource=self.backend_service,
              reason=op.prep_msg(
                  op.FAILURE_REASON,
                  insight=insight.description,
              ),
              remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
          return
        for ref in used_by_refs:
          # application load balancers (url map is central resource):
          if insight.details.get('loadBalancerUri').endswith(ref):
            op.add_metadata('insightDetail', insight.details)
            op.add_failed(
                resource=self.backend_service,
                reason=op.prep_msg(
                    op.FAILURE_REASON,
                    insight=insight.description,
                ),
                remediation=op.prep_msg(op.FAILURE_REMEDIATION),
            )
            return
    op.add_ok(self.backend_service,
              reason=op.prep_msg(op.SUCCESS_REASON,
                                 bs_url=self.backend_service.full_path))


class ValidateBackendServicePortConfiguration(runbook.Step):
  """Checks if health check sends probe requests to the different port than serving port."""

  template = 'unhealthy_backends::port_mismatch'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck

  @property
  def name(self):
    return (f'Validate port configuration for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if health check sends probe requests to the different port than serving port."""
    lb_scheme = self.backend_service.load_balancing_scheme
    if self.region != 'global' and lb_scheme in ['INTERNAL', 'EXTERNAL']:
      op.add_uncertain(
          self.backend_service,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON_ALT1,
              backend_service_name=self.backend_service_name,
              lb_scheme=lb_scheme.lower(),
              hc_name=self.health_check.name,
              hc_port=self.health_check.port,
          ),
          remediation=op.prep_msg(
              op.UNCERTAIN_REMEDIATION_ALT1,
              hc_port=self.health_check.port,
          ),
      )
      return

    if not apis.is_enabled(self.project_id, 'recommender'):
      op.add_skipped(
          crm.get_project(self.project_id),
          reason=('Checking port configuration requires Recommender API to be'
                  ' enabled'),
      )
      return

    igs = gce.get_instance_groups(op.get_context())
    insights = lb.get_lb_insights_for_a_project(self.project_id, self.region)
    for insight in insights:
      if insight.is_health_check_port_mismatch_insight:
        for info in insight.details.get('backendServiceInfos'):
          if info.get('backendServiceUri').endswith(
              self.backend_service.full_path):
            impacted_igs = [
                igs.get(self._normalize_url(x))
                for x in info.get('impactedInstanceGroupUris', [])
            ]
            formatted_igs = self._format_affected_instance_groups(
                impacted_igs, info.get('servingPortName'))
            op.add_uncertain(
                resource=self.backend_service,
                reason=op.prep_msg(
                    op.UNCERTAIN_REASON,
                    hc_port=info.get('healthCheckPortNumber'),
                    serving_port_name=info.get('servingPortName'),
                    formatted_igs=formatted_igs,
                    bs_resource=self.backend_service.full_path,
                ),
                remediation=op.prep_msg(
                    op.UNCERTAIN_REMEDIATION,
                    hc_port=info.get('healthCheckPortNumber'),
                    serving_port_name=info.get('servingPortName'),
                    bs_resource=self.backend_service.full_path,
                    project_id=self.project_id,
                ),
            )
            return
    port_name = self.backend_service.port_name
    has_negs = any('/networkEndpointGroups/' in backend.get('group')
                   for backend in self.backend_service.backends)

    if has_negs:
      port_mapping = (
          'Backend service uses Network Endpoint Groups (NEGs), portName'
          ' parameter is not applicable.')
      op.add_ok(
          self.backend_service,
          reason=op.prep_msg(op.SUCCESS_REASON, port_mapping=port_mapping),
      )
    else:
      port_mapping_details = []
      for backend in self.backend_service.backends:
        ig = igs.get(self._normalize_url(backend.get('group')))
        if ig:
          port_numbers = self._get_port_numbers_by_name(ig, port_name)
          if port_numbers:
            port_numbers_str = ', '.join(sorted(port_numbers))
            port_mapping_details.append(
                f'  {ig.full_path}: portName "{port_name}" -> port(s)'
                f' {port_numbers_str}')
          else:
            port_mapping_details.append(
                f'  {ig.full_path}: portName "{port_name}" not defined')

      if port_mapping_details:
        port_mapping = ('  Health check port specification:'
                        f' {self.health_check.port_specification}')
        if self.health_check.port_specification == 'USE_FIXED_PORT':
          port_mapping += f'\n  Health check port: {self.health_check.port}'
        port_mapping += ('\n  Backend service serving port name:'
                         f' "{port_name}"\n  Port mapping details:\n' +
                         '\n'.join(port_mapping_details))
      else:
        port_mapping = (
            f'portName "{port_name}" is not used in any instance group for this'
            ' backend service.')

      op.add_ok(
          self.backend_service,
          reason=op.prep_msg(op.SUCCESS_REASON, port_mapping=port_mapping),
      )

  def _normalize_url(self, url):
    if not url:
      return url
    try:
      # Add // prefix if scheme is missing for urlparse to work correctly
      if (not url.startswith('http://') and not url.startswith('https://') and
          not url.startswith('//')):
        temp_url = '//' + url
      else:
        temp_url = url

      parsed_url = urllib.parse.urlparse(temp_url)

      if parsed_url.hostname == 'compute.googleapis.com':
        return parsed_url.path.lstrip('/')
      elif (parsed_url.hostname == 'www.googleapis.com' and
            parsed_url.path.startswith('/compute/v1/')):
        return parsed_url.path.replace('/compute/v1/', '', 1)
      else:
        return url
    except ValueError:
      # Handle potential parsing errors
      return url

  def _format_affected_instance_groups(self, impacted_instance_groups,
                                       serving_port_name):
    output_lines = []
    for group in impacted_instance_groups:
      port_numbers = ', '.join(
          self._get_port_numbers_by_name(group, serving_port_name))
      output_lines.append(
          f'{group.full_path} - port name "{serving_port_name}" translates to'
          f' port {port_numbers}')

    return '\n'.join(output_lines)

  def _get_port_numbers_by_name(self, impacted_instance_group,
                                serving_port_name):
    return [
        str(p['port'])
        for p in impacted_instance_group.named_ports
        if p.get('name') == serving_port_name
    ]


class ValidateBackendServiceProtocolConfiguration(runbook.Step):
  """Checks if health check uses the same protocol as backend service for serving traffic."""

  template = 'unhealthy_backends::protocol_mismatch'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck

  @property
  def name(self):
    return (f'Validate protocol configuration for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if health check uses the same protocol as backend service for serving traffic."""
    if self.backend_service.protocol == 'UDP':
      op.add_skipped(
          self.backend_service,
          reason=(
              "Load balancer uses UDP protocol which doesn't make sense for"
              " health checks as it's connectionless and doesn't have built-in"
              ' features for acknowledging delivery'),
      )
      return

    if self.health_check.type == self.backend_service.protocol:
      op.add_ok(
          self.backend_service,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             bs_resource=self.backend_service.full_path,
                             hc_protocol=self.health_check.type),
      )
    elif self.health_check.type == 'TCP':
      op.add_ok(
          self.backend_service,
          reason=op.prep_msg(op.SUCCESS_REASON_ALT1,
                             bs_resource=self.backend_service.full_path,
                             serving_protocol=self.backend_service.protocol),
      )
    else:
      op.add_uncertain(
          self.backend_service,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              hc_protocol=self.health_check.type,
              serving_protocol=self.backend_service.protocol,
              bs_resource=self.backend_service.full_path,
          ),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,),
      )


class VerifyHealthCheckLoggingEnabled(runbook.Gateway):
  """Check if health check logging is enabled."""

  template = 'unhealthy_backends::logging_enabled'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck
  backend_health_statuses: List[lb.BackendHealth]

  @property
  def name(self):
    return (f'Verify health check logging enabled for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Check if health check logging is enabled and create child steps if so."""
    if self.health_check.is_log_enabled:
      op.add_ok(
          self.health_check,
          reason=op.prep_msg(op.SUCCESS_REASON,
                             hc_url=self.health_check.full_path),
      )
      analyze_latest_hc_log = AnalyzeLatestHealthCheckLog()
      analyze_latest_hc_log.project_id = self.project_id
      analyze_latest_hc_log.backend_service_name = self.backend_service_name
      analyze_latest_hc_log.region = self.region
      analyze_latest_hc_log.backend_service = self.backend_service
      analyze_latest_hc_log.health_check = self.health_check
      analyze_latest_hc_log.backend_health_statuses = self.backend_health_statuses
      self.add_child(analyze_latest_hc_log)

      check_past_hc_success = CheckPastHealthCheckSuccess()
      check_past_hc_success.project_id = self.project_id
      check_past_hc_success.backend_service_name = self.backend_service_name
      check_past_hc_success.region = self.region
      check_past_hc_success.backend_service = self.backend_service
      check_past_hc_success.backend_health_statuses = self.backend_health_statuses
      self.add_child(check_past_hc_success)
    else:
      additional_flags = ''
      if self.region != 'global':
        additional_flags = f'--region={self.region} '
      op.add_uncertain(
          self.backend_service,
          reason=op.prep_msg(op.UNCERTAIN_REASON,
                             hc_url=self.health_check.full_path),
          remediation=op.prep_msg(
              op.UNCERTAIN_REMEDIATION,
              hc_name=self.health_check.name,
              protocol=self.health_check.type.lower(),
              additional_flags=additional_flags,
          ),
      )


class AnalyzeLatestHealthCheckLog(runbook.Gateway):
  """Look for the latest health check logs and based on that decide what to do next."""

  template = 'unhealthy_backends::health_check_log'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck
  backend_health_statuses: List[lb.BackendHealth]

  @property
  def name(self):
    return (f'Analyze latest health check log for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Look for the latest health check logs and based on that decide what to do next."""
    # Find all groups that have at least one unhealthy instance
    unhealthy_groups = {
        state.group
        for state in self.backend_health_statuses
        if state.health_state == 'UNHEALTHY'
    }

    check_window = timedelta(days=14)
    if not unhealthy_groups:
      unhealthy_groups = {state.group for state in self.backend_health_statuses}
      check_window = timedelta(minutes=10)

    detailed_health_states = {}

    # Add support for NEGs
    for group in unhealthy_groups:
      m = re.search(r'/(?:regions|zones)/([^/?]+)/([^/?]+)/([^/?]+)', group)
      if not m:
        raise RuntimeError(
            "Can't determine region or zone or group name from self links"
            f' {group}')

      location = m.group(1)
      resource_type = m.group(2)
      resource_name = m.group(3)

      if resource_type == 'instanceGroups':
        filter_str = """resource.type="gce_instance_group"
                        log_name="projects/{}/logs/compute.googleapis.com%2Fhealthchecks"
                        resource.labels.instance_group_name="{}"
                        resource.labels.location=~"{}"
                        jsonPayload.healthCheckProbeResult.healthState="UNHEALTHY"
                        """.format(self.project_id, resource_name, location)
      elif resource_type == 'networkEndpointGroups':
        network_endpoint_group = _get_zonal_network_endpoint_group(
            self.project_id, location, resource_name)
        if network_endpoint_group:
          filter_str = """resource.type="gce_network_endpoint_group"
                        log_name="projects/{}/logs/compute.googleapis.com%2Fhealthchecks"
                        resource.labels.network_endpoint_group_id="{}"
                        resource.labels.zone={}
                        jsonPayload.healthCheckProbeResult.healthState="UNHEALTHY"
                        """.format(self.project_id, network_endpoint_group.id,
                                   location)
        else:
          op.add_skipped(
              resource=self.backend_service,
              reason=(
                  f'Network endpoint group {resource_name} in zone {location} '
                  f'does not exist in project {self.project_id}'),
          )
          continue
      else:
        op.add_skipped(
            resource=self.backend_service,
            reason=(f'Unsupported resource type {resource_type} for group'
                    f' {group} in backend service'
                    f' {self.backend_service_name} in scope'
                    f' {self.region}'),
        )
        continue
      serial_log_entries = logs.realtime_query(
          project_id=self.project_id,
          filter_str=filter_str,
          start_time=datetime.now() - check_window,
          end_time=datetime.now(),
          disable_paging=True,
      )

      if serial_log_entries:
        last_log = serial_log_entries.pop()
        op.add_metadata('log', last_log)
        if (get_path(
            last_log,
            'jsonPayload.healthCheckProbeResult.healthState') == 'UNHEALTHY'):
          detailed_health_states.setdefault(
              get_path(
                  last_log,
                  'jsonPayload.healthCheckProbeResult.detailedHealthState',
              ),
              [],
          ).append(get_path(last_log, 'jsonPayload.healthCheckProbeResult'))

    if detailed_health_states.get('TIMEOUT'):
      timeout_hc_log_step = AnalyzeTimeoutHealthCheckLog()
      timeout_hc_log_step.project_id = self.project_id
      timeout_hc_log_step.backend_service_name = self.backend_service_name
      timeout_hc_log_step.region = self.region
      timeout_hc_log_step.logs = detailed_health_states.get('TIMEOUT')
      timeout_hc_log_step.backend_service = self.backend_service
      timeout_hc_log_step.health_check = self.health_check
      self.add_child(timeout_hc_log_step)
    if detailed_health_states.get('UNHEALTHY'):
      unhealthy_hc_log_step = AnalyzeUnhealthyHealthCheckLog()
      unhealthy_hc_log_step.project_id = self.project_id
      unhealthy_hc_log_step.backend_service_name = self.backend_service_name
      unhealthy_hc_log_step.region = self.region
      unhealthy_hc_log_step.logs = detailed_health_states.get('UNHEALTHY')
      unhealthy_hc_log_step.backend_service = self.backend_service
      unhealthy_hc_log_step.health_check = self.health_check
      self.add_child(unhealthy_hc_log_step)
    if detailed_health_states.get('UNKNOWN'):
      unknown_hc_log_step = AnalyzeUnknownHealthCheckLog()
      unknown_hc_log_step.project_id = self.project_id
      unknown_hc_log_step.backend_service_name = self.backend_service_name
      unknown_hc_log_step.region = self.region
      unknown_hc_log_step.backend_service = self.backend_service
      self.add_child(unknown_hc_log_step)


class AnalyzeTimeoutHealthCheckLog(runbook.Step):
  """Analyzes logs with the detailed health check state TIMEOUT"""

  logs: list[dict]
  template = 'unhealthy_backends::timeout_hc_state_log'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck

  @property
  def name(self):
    return (f'Analyze TIMEOUT health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyzes logs with the detailed health check state TIMEOUT"""
    if not self.logs:
      op.add_skipped(
          self.backend_service,
          reason='No logs with detailed health state TIMEOUT found',
      )
      return

    probe_results_texts = {
        get_path(log, 'probeResultText') for log in self.logs
    }
    probe_results_text_str = ', '.join(f'"{x}"' for x in probe_results_texts)
    try:
      success_criteria = get_health_check_success_criteria(self.health_check)
    except ValueError as e:
      op.add_skipped(
          self.backend_service,
          reason=f'Health check type is not supported: {e}',
      )
      return

    op.add_uncertain(
        self.backend_service,
        reason=op.prep_msg(op.FAILURE_REASON,
                           probe_results_text_str=probe_results_text_str,
                           bs_url=self.backend_service.full_path),
        remediation=op.prep_msg(
            op.FAILURE_REMEDIATION,
            success_criteria=success_criteria,
            bs_timeout_sec=self.backend_service.timeout_sec or 30,
            hc_timeout_sec=self.health_check.timeout_sec,
        ),
    )


class AnalyzeUnhealthyHealthCheckLog(runbook.Step):
  """Analyzes logs with detailed health state UNHEALTHY."""

  template = 'unhealthy_backends::unhealthy_hc_state_log'
  logs: list[dict]
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  health_check: gce.HealthCheck

  @property
  def name(self):
    return (f'Analyze UNHEALTHY health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyzes logs with detailed health state UNHEALTHY."""
    if not self.logs:
      op.add_skipped(
          self.backend_service,
          reason='No logs with detailed health state UNHEALTHY found',
      )
      return

    try:
      success_criteria = get_health_check_success_criteria(self.health_check)
    except ValueError as e:
      op.add_skipped(
          self.backend_service,
          reason=f'Health check type is not supported: {e}',
      )
      return

    probe_results_texts = {
        get_path(log, 'probeResultText') for log in self.logs
    }
    probe_results_text_str = ', '.join(f'"{x}"' for x in probe_results_texts)

    op.add_uncertain(
        self.backend_service,
        reason=op.prep_msg(op.FAILURE_REASON,
                           probe_results_text_str=probe_results_text_str,
                           bs_url=self.backend_service.full_path),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                success_criteria=success_criteria),
    )


class AnalyzeUnknownHealthCheckLog(runbook.Step):
  """Analyze logs with detailed health state UNKNOWN."""

  template = 'unhealthy_backends::unknown_hc_state_log'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices

  @property
  def name(self):
    return (f'Analyze UNKNOWN health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyze logs with detailed health state UNKNOWN."""
    op.add_uncertain(
        self.backend_service,
        reason=op.prep_msg(op.FAILURE_REASON,
                           bs_url=self.backend_service.full_path),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
    )


class CheckPastHealthCheckSuccess(runbook.Step):
  """Checks if the health check has worked successfully in the past."""

  template = 'unhealthy_backends::past_hc_success'
  project_id: str
  backend_service_name: str
  region: str
  backend_service: lb.BackendServices
  backend_health_statuses: List[lb.BackendHealth]

  @property
  def name(self):
    return (f'Check past health check success for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if the health check has worked successfully in the past."""
    unhealthy_groups = {
        state.group
        for state in self.backend_health_statuses
        if state.health_state == 'UNHEALTHY'
    }
    any_date_found = False
    message = ''
    # Add support for NEGs
    for group in unhealthy_groups:
      m = re.search(r'/(?:regions|zones)/([^/?]+)/([^/?]+)/([^/?]+)', group)
      if not m:
        raise RuntimeError(
            "Can't determine region or zone or instanceGroup name from ig"
            f' {group}')

      location = m.group(1)
      resource_type = m.group(2)
      resource_name = m.group(3)

      if resource_type == 'instanceGroups':
        filter_str = """resource.type="gce_instance_group"
                          log_name="projects/{}/logs/compute.googleapis.com%2Fhealthchecks"
                          resource.labels.instance_group_name="{}"
                          resource.labels.location={}
                          jsonPayload.healthCheckProbeResult.previousHealthState="HEALTHY"
                          jsonPayload.healthCheckProbeResult.detailedHealthState="TIMEOUT"
                          OR "UNHEALTHY" OR "UNKNOWN" """.format(
            self.project_id, resource_name, location)
      elif resource_type == 'networkEndpointGroups':
        network_endpoint_group = _get_zonal_network_endpoint_group(
            self.project_id, location, resource_name)
        if network_endpoint_group:
          filter_str = """resource.type="gce_network_endpoint_group"
                            log_name="projects/{}/logs/compute.googleapis.com%2Fhealthchecks"
                            resource.labels.network_endpoint_group_id="{}"
                            resource.labels.zone={}
                            jsonPayload.healthCheckProbeResult.previousHealthState="HEALTHY"
                            jsonPayload.healthCheckProbeResult.detailedHealthState="TIMEOUT"
                            OR "UNHEALTHY" OR "UNKNOWN" """.format(
              self.project_id, network_endpoint_group.id, location)
        else:
          op.add_skipped(
              resource=group,
              reason=(
                  f'Network endpoint group {resource_name} in zone {location} '
                  f'does not exist in project {self.project_id}'),
          )
          continue
      else:
        op.add_skipped(
            resource=group,
            reason=(f'Unsupported resource type {resource_type} for group'
                    f' {group} in backend service'
                    f' {self.backend_service_name} in scope'
                    f' {self.region}'),
        )
        continue

      serial_log_entries = logs.realtime_query(
          project_id=self.project_id,
          filter_str=filter_str,
          start_time=datetime.now() - timedelta(days=14),
          end_time=datetime.now(),
          disable_paging=True,
      )

      if serial_log_entries:
        last_log = serial_log_entries.pop()
        timestamp = get_path(last_log, 'receiveTimestamp')
        any_date_found = True
        op.add_metadata(group, timestamp)
        message += (f'{group}: Backends transitioned to an unhealthy state at'
                    f' {timestamp}\n\n')
      else:
        message += (
            f'{group}: No logs were found indicating HEALTHY -> UNHEALTHY'
            ' transition \n\n')

    if message and any_date_found:
      op.add_uncertain(
          self.backend_service,
          reason=message,
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                  bs_url=self.backend_service.full_path),
      )
    else:
      op.add_skipped(
          self.backend_service,
          reason=('No past health check success found in the logs for the '
                  f'backend service {self.backend_service.full_path}'),
      )


class UnhealthyBackendsEnd(runbook.EndStep):
  """Concludes the unhealthy backends diagnostics process.

  If the issue persists, it directs the user to helpful
  resources and suggests contacting support with a detailed report.
  """

  def execute(self):
    """Finalize unhealthy backends diagnostics."""
    if not config.get(flags.INTERACTIVE_MODE):
      region = op.get(flags.REGION, 'global')
      backend_service_name = op.get(flags.BACKEND_SERVICE_NAME)
      response = op.prompt(
          kind=op.CONFIRMATION,
          message=(
              'Are you still experiencing health check issues on the backend'
              f' service {backend_service_name} in scope'
              f' {region}?'),
          choice_msg='Enter an option: ',
      )
      if response == op.NO:
        op.info(message=op.END_MESSAGE)


def get_health_check_success_criteria(health_check: gce.HealthCheck):
  """Constructs a human-readable description of a health check's success criteria."""

  success_criteria = (
      f'The health check is using {health_check.type} protocol, and ')

  port = ('serving port' if health_check.port_specification
          == 'USE_SERVING_PORT' else f'port {health_check.port}')

  if health_check.type in ['HTTP', 'HTTPS', 'HTTP2']:
    success_criteria += (
        'it is set to: \n- send a prober requests to the'
        f' {health_check.request_path} path on {port} \n- expect a response'
        ' with an HTTP 200 (OK) status code')
    if health_check.response:
      success_criteria += (
          f' and response body containing the string "{health_check.response}"')

  elif health_check.type in ['TCP', 'SSL']:
    success_criteria += f'it is set to: \n- send a prober requests on {port}'
    if health_check.request:
      success_criteria += (
          f' with the configured request string "{health_check.request}"')
    success_criteria += f'\n- expect a successful {health_check.type} handshake'
    if health_check.response:
      success_criteria += (
          f' and the response string exactly matches: "{health_check.response}"'
      )

  elif health_check.type == 'GRPC':
    success_criteria += (
        f' it is set to: \n- send a prober requests on {port} \n- expect a RPC'
        ' response with the status OK and the status field set to SERVING')

  else:
    raise ValueError(f'Unsupported health check type: {health_check.type}')

  return success_criteria


def _get_timing_and_threshold_info(health_check: gce.HealthCheck) -> str:
  """Constructs a human-readable description of a health check's timing and threshold settings."""

  timing_and_threshold = (
      f'The health check is configured with the following timing and threshold'
      f' settings:\n- **Check Interval:** A health check is performed every'
      f' {health_check.check_interval_sec} seconds.\n- **Timeout:** The prober'
      f' will wait up to {health_check.timeout_sec} seconds for a'
      f' response.\n- **Healthy Threshold:** It takes'
      f' {health_check.healthy_threshold} consecutive successes for a backend to'
      f' be considered healthy.\n- **Unhealthy Threshold:** It takes'
      f' {health_check.unhealthy_threshold} consecutive failures for a backend'
      f' to be considered unhealthy.')

  return timing_and_threshold


def _get_zonal_network_endpoint_group(
    project: str, zone: str, name: str) -> Optional[gce.NetworkEndpointGroup]:
  """Returns a map of Network Endpoint Groups in the project."""
  groups = gce.get_zonal_network_endpoint_groups(op.get_context())
  url = f"""projects/{project}/zones/{zone}/networkEndpointGroups/{name}"""

  if url in groups:
    return groups[url]
  else:
    return None
