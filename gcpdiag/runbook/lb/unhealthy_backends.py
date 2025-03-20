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
from datetime import datetime, timedelta
from itertools import groupby
from typing import Optional

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
    """Building Decision Tree"""

    project_id = op.get(flags.PROJECT_ID)
    backend_service_name = op.get(flags.BACKEND_SERVICE_NAME)
    region = op.get(flags.REGION, 'global')

    start = UnhealthyBackendsStart()
    start.project_id = project_id
    start.backend_service_name = backend_service_name
    start.region = region

    self.add_start(start)

    logging_check = VerifyHealthCheckLoggingEnabled()
    logging_check.project_id = project_id
    logging_check.backend_service_name = backend_service_name
    logging_check.region = region
    self.add_step(parent=start, child=logging_check)

    port_check = ValidateBackendServicePortConfiguration()
    port_check.project_id = project_id
    port_check.backend_service_name = backend_service_name
    port_check.region = region
    self.add_step(parent=start, child=port_check)

    protocol_check = ValidateBackendServiceProtocolConfiguration()
    protocol_check.project_id = project_id
    protocol_check.backend_service_name = backend_service_name
    protocol_check.region = region
    self.add_step(parent=start, child=protocol_check)

    firewall_check = VerifyFirewallRules()
    firewall_check.project_id = project_id
    firewall_check.backend_service_name = backend_service_name
    firewall_check.region = region
    self.add_step(parent=start, child=firewall_check)

    vm_performance_check = CheckVmPerformance()
    vm_performance_check.project_id = project_id
    vm_performance_check.backend_service_name = backend_service_name
    vm_performance_check.region = region

    self.add_step(parent=start, child=vm_performance_check)

    # Ending your runbook
    self.add_end(UnhealthyBackendsEnd())


class UnhealthyBackendsStart(runbook.StartStep):
  """Start step for Unhealthy Backends runbook."""

  template = 'unhealthy_backends::confirmation'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Analyze unhealthy backends for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks the health of a specified load balancer's backends."""

    proj = crm.get_project(self.project_id)

    if not apis.is_enabled(self.project_id, 'compute'):
      op.add_skipped(proj, reason='Compute API is not enabled')
      return  # Early exit if Compute API is disabled

    try:
      op.info(f'name: {self.backend_service_name}, region:'
              f' {self.region}')
      backend_service = lb.get_backend_service(
          self.project_id,
          self.backend_service_name,
          self.region,
      )
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          proj,
          reason=(f'Backend service {self.backend_service_name} does not'
                  f' exist in scope {self.region} or project'
                  f' {self.project_id}'),
      )
      return  # Early exit if load balancer doesn't exist

    backend_health_statuses = lb.get_backend_service_health(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    if not backend_health_statuses:
      op.add_skipped(
          proj,
          reason=(f'Backend service {self.backend_service_name} does not'
                  f' have any backends in scope {self.region} or'
                  f' project {self.project_id}'),
      )
      return  # Early exit if load balancer doesn't have any backends

    unhealthy_backends = [
        backend for backend in backend_health_statuses
        if backend.health_state == 'UNHEALTHY'
    ]

    backend_health_statuses_per_group = {
        k: list(v)
        for k, v in groupby(backend_health_statuses, key=lambda x: x.group)
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
          resource=backend_service,
          reason=op.prep_msg(
              op.FAILURE_REASON,
              name=self.backend_service_name,
              region=self.region,
              detailed_reason=detailed_reason,
          ),
          remediation='',
      )
    else:
      op.add_ok(
          resource=backend_service,
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
    backend_health_statuses = lb.get_backend_service_health(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    instances_to_analyze_by_group = {}

    for status in sorted(
        backend_health_statuses,
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

      mem_check = gce_gs.HighVmMemoryUtilization()
      mem_check.project_id = project_id
      mem_check.zone = zone
      mem_check.instance_name = instance_name
      disk_check = gce_gs.HighVmDiskUtilization()
      disk_check.project_id = project_id
      disk_check.zone = zone
      disk_check.instance_name = instance_name
      cpu_check = gce_gs.HighVmCpuUtilization()
      cpu_check.project_id = project_id
      cpu_check.zone = zone
      cpu_check.instance_name = instance_name

      self.add_child(mem_check)
      self.add_child(disk_check)
      self.add_child(cpu_check)


class VerifyFirewallRules(runbook.Step):
  """Checks if firewall rules are configured correctly."""

  template = 'unhealthy_backends::firewall_rules'
  project_id: str
  backend_service_name: str
  region: str

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
      return  # Early exit if Recommender API is disabled

    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    used_by_refs = backend_service.used_by_refs
    insights = lb.get_lb_insights_for_a_project(self.project_id, self.region)
    for insight in insights:
      if insight.is_firewall_rule_insight and insight.details.get(
          'loadBalancerUri'):
        # network load balancers (backend service is central resource):
        if insight.details.get('loadBalancerUri').endswith(
            backend_service.full_path):
          op.add_metadata('insightDetail', insight.details)
          op.add_failed(
              resource=backend_service,
              reason=op.prep_msg(
                  op.FAILURE_REASON,
                  insight=insight.description,
              ),
              remediation=op.prep_msg(op.FAILURE_REMEDIATION),
          )
          return  # Exit the loop after finding a match
        for ref in used_by_refs:
          # application load balancers (url map is central resource):
          if insight.details.get('loadBalancerUri').endswith(ref):
            op.add_metadata('insightDetail', insight.details)
            op.add_failed(
                resource=backend_service,
                reason=op.prep_msg(
                    op.FAILURE_REASON,
                    insight=insight.description,
                ),
                remediation=op.prep_msg(op.FAILURE_REMEDIATION),
            )
            return  # Exit the loop after finding a match
    op.add_ok(backend_service,
              reason=op.prep_msg(op.SUCCESS_REASON,
                                 bs_url=backend_service.full_path))


class ValidateBackendServicePortConfiguration(runbook.Step):
  """Checks if health check sends probe requests to the different port than serving port."""

  template = 'unhealthy_backends::port_mismatch'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Validate port configuration for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if health check sends probe requests to the different port than serving port."""
    if not apis.is_enabled(self.project_id, 'recommender'):
      op.add_skipped(
          crm.get_project(self.project_id),
          reason=('Checking port configuration requires Recommender API to be'
                  ' enabled'),
      )
      return  # Early exit if Recommender API is disabled

    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )
    igs = gce.get_instance_groups(
        op.get_new_context(project_id=op.get(flags.PROJECT_ID)))
    insights = lb.get_lb_insights_for_a_project(self.project_id, self.region)
    for insight in insights:
      if insight.is_health_check_port_mismatch_insight:
        for info in insight.details.get('backendServiceInfos'):
          if info.get('backendServiceUri').endswith(backend_service.full_path):
            impacted_igs = [
                igs.get(self._normalize_url(x))
                for x in info.get('impactedInstanceGroupUris', [])
            ]
            formatted_igs = self._format_affected_instance_groups(
                impacted_igs, info.get('servingPortName'))
            op.add_uncertain(
                resource=backend_service,
                reason=op.prep_msg(
                    op.UNCERTAIN_REASON,
                    hc_port=info.get('healthCheckPortNumber'),
                    serving_port_name=info.get('servingPortName'),
                    formatted_igs=formatted_igs,
                    bs_resource=backend_service.full_path,
                ),
                remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION),
            )
            return  # Exit the loop after finding a match
    op.add_ok(backend_service, reason=op.prep_msg(op.SUCCESS_REASON))

  def _normalize_url(self, url):
    return url.split('//compute.googleapis.com/')[1]

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

  @property
  def name(self):
    return (f'Validate protocol configuration for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if health check uses the same protocol as backend service for serving traffic."""

    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    health_check = gce.get_health_check(
        self.project_id,
        backend_service.health_check,
        backend_service.region,
    )

    if backend_service.protocol == 'UDP':
      op.add_skipped(
          backend_service,
          reason=(
              "Load balancer uses UDP protocol which doesn't make sense for"
              " health checks as it's connectionless and doesn't have built-in"
              ' features for acknowledging delivery'),
      )
      return
    if health_check.type == backend_service.protocol:
      op.add_ok(
          backend_service,
          reason=op.prep_msg(op.SUCCESS_REASON, hc_protocol=health_check.type),
      )
    else:
      op.add_uncertain(
          backend_service,
          reason=op.prep_msg(
              op.UNCERTAIN_REASON,
              hc_protocol=health_check.type,
              serving_protocol=backend_service.protocol,
              bs_resource=backend_service.full_path,
          ),
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,),
      )


class VerifyHealthCheckLoggingEnabled(runbook.Gateway):
  """Check if health check logging is enabled."""

  template = 'unhealthy_backends::logging_enabled'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Verify health check logging enabled for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Check if health check logging is enabled."""
    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )
    health_check = gce.get_health_check(
        self.project_id,
        backend_service.health_check,
        backend_service.region,
    )

    if health_check.is_log_enabled:
      op.add_ok(
          health_check,
          reason=op.prep_msg(op.SUCCESS_REASON, hc_url=health_check.full_path),
      )
      analyze_latest_hc_log = AnalyzeLatestHealthCheckLog()
      analyze_latest_hc_log.project_id = self.project_id
      analyze_latest_hc_log.backend_service_name = self.backend_service_name
      analyze_latest_hc_log.region = self.region
      self.add_child(analyze_latest_hc_log)

      check_past_hc_success = CheckPastHealthCheckSuccess()
      check_past_hc_success.project_id = self.project_id
      check_past_hc_success.backend_service_name = self.backend_service_name
      check_past_hc_success.region = self.region
      self.add_child(check_past_hc_success)
    else:
      additional_flags = ''
      if self.region != 'global':
        additional_flags = f'--region={self.region} '
      op.add_uncertain(
          backend_service,
          reason=op.prep_msg(op.UNCERTAIN_REASON,
                             hc_url=health_check.full_path),
          remediation=op.prep_msg(
              op.UNCERTAIN_REMEDIATION,
              hc_name=health_check.name,
              protocol=health_check.type,
              additional_flags=additional_flags,
          ),
      )


class AnalyzeLatestHealthCheckLog(runbook.Gateway):
  """Look for the latest health check logs and based on that decide what to do next."""

  template = 'unhealthy_backends::health_check_log'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):

    return (f'Analyze latest health check log for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Look for the latest health check logs and based on that decide what to do next."""
    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )
    health_checks_states = lb.get_backend_service_health(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    # Find all groups that have at least one unhealthy instance
    unhealthy_groups = {
        state.group
        for state in health_checks_states
        if state.health_state == 'UNHEALTHY'
    }

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
              resource=backend_service,
              reason=(
                  f'Network endpoint group {resource_name} in zone {location} '
                  f'does not exist in project {self.project_id}'),
          )
          continue
      else:
        op.add_skipped(
            resource=backend_service,
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
      self.add_child(timeout_hc_log_step)
    if detailed_health_states.get('UNHEALTHY'):
      unhealthy_hc_log_step = AnalyzeUnhealthyHealthCheckLog()
      unhealthy_hc_log_step.project_id = self.project_id
      unhealthy_hc_log_step.backend_service_name = self.backend_service_name
      unhealthy_hc_log_step.region = self.region
      unhealthy_hc_log_step.logs = detailed_health_states.get('UNHEALTHY')
      self.add_child(unhealthy_hc_log_step)
    if detailed_health_states.get('UNKNOWN'):
      unknown_hc_log_step = AnalyzeUnknownHealthCheckLog()
      unknown_hc_log_step.project_id = self.project_id
      unknown_hc_log_step.backend_service_name = self.backend_service_name
      unknown_hc_log_step.region = self.region

      self.add_child(unknown_hc_log_step)


class AnalyzeTimeoutHealthCheckLog(runbook.Step):
  """Analyzes logs with the detailed health check state TIMEOUT"""

  logs: list[dict]
  template = 'unhealthy_backends::timeout_hc_state_log'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Analyze TIMEOUT health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyzes logs with the detailed health check state TIMEOUT"""
    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    if not self.logs:
      op.add_skipped(
          backend_service,
          reason='No logs with detailed health state TIMEOUT found',
      )
      return

    health_check = gce.get_health_check(
        self.project_id,
        backend_service.health_check,
        backend_service.region,
    )

    probe_results_texts = {
        get_path(log, 'probeResultText') for log in self.logs
    }
    probe_results_text_str = ', '.join(f'"{x}"' for x in probe_results_texts)
    try:
      success_criteria = get_health_check_success_criteria(health_check)
    except ValueError as e:
      op.add_skipped(
          backend_service,
          reason=f'Health check type is not supported: {e}',
      )
      return

    op.add_uncertain(
        backend_service,
        reason=op.prep_msg(op.FAILURE_REASON,
                           probe_results_text_str=probe_results_text_str,
                           bs_url=backend_service.full_path),
        remediation=op.prep_msg(
            op.FAILURE_REMEDIATION,
            success_criteria=success_criteria,
            bs_timeout_sec=backend_service.timeout_sec or 30,
            hc_timeout_sec=health_check.timeout_sec,
        ),
    )


class AnalyzeUnhealthyHealthCheckLog(runbook.Step):
  """Analyzes logs with detailed health state UNHEALTHY."""

  template = 'unhealthy_backends::unhealthy_hc_state_log'
  logs: list[dict]
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Analyze UNHEALTHY health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyzes logs with detailed health state UNHEALTHY."""

    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    if not self.logs:
      op.add_skipped(
          backend_service,
          reason='No logs with detailed health state UNHEALTHY found',
      )
      return

    health_check = gce.get_health_check(
        self.project_id,
        backend_service.health_check,
        backend_service.region,
    )

    try:
      success_criteria = get_health_check_success_criteria(health_check)
    except ValueError as e:
      op.add_skipped(
          backend_service,
          reason=f'Health check type is not supported: {e}',
      )
      return

    probe_results_texts = {
        get_path(log, 'probeResultText') for log in self.logs
    }
    probe_results_text_str = ', '.join(f'"{x}"' for x in probe_results_texts)

    op.add_uncertain(
        backend_service,
        reason=op.prep_msg(op.FAILURE_REASON,
                           probe_results_text_str=probe_results_text_str,
                           bs_url=backend_service.full_path),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                success_criteria=success_criteria),
    )


class AnalyzeUnknownHealthCheckLog(runbook.Step):
  """Analyze logs with detailed health state UNKNOWN."""

  template = 'unhealthy_backends::unknown_hc_state_log'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Analyze UNKNOWN health check logs for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Analyze logs with detailed health state UNKNOWN."""
    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )
    op.add_uncertain(
        backend_service,
        reason=op.prep_msg(op.FAILURE_REASON, bs_url=backend_service.full_path),
        remediation=op.prep_msg(op.FAILURE_REMEDIATION),
    )


class CheckPastHealthCheckSuccess(runbook.Step):
  """Checks if the health check has worked successfully in the past."""

  template = 'unhealthy_backends::past_hc_success'
  project_id: str
  backend_service_name: str
  region: str

  @property
  def name(self):
    return (f'Check past health check success for backend service'
            f' "{self.backend_service_name}" in scope'
            f' "{self.region}".')

  def execute(self):
    """Checks if the health check has worked successfully in the past."""
    backend_service = lb.get_backend_service(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    health_checks_states = lb.get_backend_service_health(
        self.project_id,
        self.backend_service_name,
        self.region,
    )

    unhealthy_groups = {
        state.group
        for state in health_checks_states
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
          backend_service,
          reason=message,
          remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION,
                                  bs_url=backend_service.full_path),
      )
    else:
      op.add_skipped(
          backend_service,
          reason=(
              'No past health check success found in the logs for the backend'
              f' service {backend_service.full_path}'),
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
      f'Your health check is using {health_check.type} protocol, and ')

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


def _get_zonal_network_endpoint_group(
    project: str, zone: str, name: str) -> Optional[gce.NetworkEndpointGroup]:
  """Returns a map of Network Endpoint Groups in the project."""
  groups = gce.get_zonal_network_endpoint_groups(
      op.get_new_context(project_id=project))
  url = f"""projects/{project}/zones/{zone}/networkEndpointGroups/{name}"""

  if url in groups:
    return groups[url]
  else:
    return None
