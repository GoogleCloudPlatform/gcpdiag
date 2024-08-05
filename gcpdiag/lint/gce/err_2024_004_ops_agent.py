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
"""Verify Ops Agent is installed on GCE VMs and is sending logs and metrics.

Why isn't the Ops Agent transmitting logs and metrics?

Please run the Agent health check
(https://cloud.google.com/stackdriver/docs/solutions/agents/\
    ops-agent/troubleshoot-find-info#start-checks)
to find out,
and look up the error code table
(https://cloud.google.com/stackdriver/docs/solutions/agents/\
    ops-agent/troubleshoot-find-info#health-checks)
to locate the corresponding fix.

To install the latest version of Ops Agent, please follow:
https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/\
    installation#install-latest-version.

To troubleshoot Ops Agent installation failure, please follow:
https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/\
    troubleshoot-install-startup#install-failed.


Top Reasons Why Ops Agent Fails to Send Logs and Metrics:
1. VM Access Scopes: The VM needs "logging.write" and "monitoring.write" scopes.
2. Service Account IAM Roles: The Service Account associated with the VM
requires "roles/monitoring.metricWriter" and "roles/logging.logWriter".
3. GCP API Enablement: Ops Agent requires Cloud Monitoring API and Cloud Logging
API enabled on the project.
"""
import logging
import operator as op
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Sequence

from gcpdiag import lint, models
from gcpdiag.queries import gce, logs, monitoring, osconfig

_query_results_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}
_syslog_query = {}
_windows_event_log_query = {}
_health_log_query = {}
OPS_AGENT_PACKAGE_NAME = 'google-cloud-ops-agent'
OPS_AGENT_LOGGING_METRICS_VERSION = 'google-cloud-ops-agent-metrics'
OPS_AGENT_MONITORING_METRICS_VERSION = 'google-cloud-ops-agent-logging'
OPS_AGENT_NOT_INSTALLED_TEXT = 'Ops Agent not installed on the VM'
OPS_AGENT_UNDETECTABLE_TEXT = 'Unable to confirm Ops Agent installation'

UNABLE_TO_DETECT_EXPLANATION = (
    'VM Manager is needed for the ops agent detection. Please enable it at:'
    ' https://cloud.google.com/compute/docs/manage-os#automatic and run this'
    ' check again.')
OPS_AGENT_OK_TEXT = (
    'Ops Agent installed on the VM, and is successfully sending logs and'
    ' metrics.')
OPS_AGENT_FAILS_TO_SEND_TELEMETRY_TEXT = (
    "Ops Agent is installed, but it's failing to send both logs and metrics"
    ' to Google Cloud.')

OPS_AGENT_FAILS_TO_SEND_TELEMETRY_EXPLANATION = (
    """\tIs Ops Agent sending logs? (%s) \tIs Ops Agent sending metrics? (%s)"""
)


class Instance:
  """Instance represents a Google Compute Engine (GCE) instance,

  storing its associated project ID and providing flags to track the Ops Agent
  installation status, OS inventory availability, and Ops Agent liveliness.
  """

  _gce_instance: gce.Instance
  _project_id: str
  _ops_agent_installed: bool
  _has_os_inventory: bool
  _has_recent_log_pings: bool
  _has_recent_log_entries: bool
  _has_logging_uptime_metrics: bool
  _has_monitoring_uptime_metrics: bool

  def __init__(self, project_id, gce_instance):

    self._gce_instance = gce_instance
    self._project_id = project_id
    self._ops_agent_installed = False
    self._has_os_inventory = False
    self._has_recent_log_pings = False
    self._has_recent_log_entries = False
    self._has_logging_uptime_metrics = False
    self._has_monitoring_uptime_metrics = False

  @property
  def project_id(self) -> str:
    return self._project_id

  @property
  def gce_instance(self) -> gce.Instance:
    return self._gce_instance

  @property
  def is_gke_node(self) -> bool:
    return self._gce_instance.is_gke_node()

  @property
  def id(self) -> str:
    return self._gce_instance.id

  @property
  def zone(self) -> str:
    return self._gce_instance.zone

  @property
  def name(self) -> str:
    return self._gce_instance.name

  @property
  def has_os_inventory(self) -> bool:
    return self._has_os_inventory

  @has_os_inventory.setter
  def has_os_inventory(self, new_value: bool):
    self._has_os_inventory = new_value

  @property
  def ops_agent_installed(self) -> bool:
    return self._ops_agent_installed

  @ops_agent_installed.setter
  def ops_agent_installed(self, new_value: bool):
    self._ops_agent_installed = new_value

  @property
  def has_recent_log_pings(self) -> bool:
    return self._has_recent_log_pings

  @has_recent_log_pings.setter
  def has_recent_log_pings(self, new_value: bool):
    self._has_recent_log_pings = new_value

  @property
  def has_recent_log_entries(self) -> bool:
    return self._has_recent_log_entries

  @has_recent_log_entries.setter
  def has_recent_log_entries(self, new_value: bool):
    self._has_recent_log_entries = new_value

  @property
  def has_logging_uptime_metrics(self) -> bool:
    return self._has_logging_uptime_metrics

  @has_logging_uptime_metrics.setter
  def has_logging_uptime_metrics(self, new_value: bool):
    self._has_logging_uptime_metrics = new_value

  @property
  def has_monitoring_uptime_metrics(self) -> bool:
    return self._has_monitoring_uptime_metrics

  @has_monitoring_uptime_metrics.setter
  def has_monitoring_uptime_metrics(self, new_value: bool):
    self._has_monitoring_uptime_metrics = new_value


def prepare_rule(context: models.Context):
  # Fetch agent uptime metrics.
  _query_results_project_id[context.project_id] = monitoring.query(
      context.project_id,
      """
fetch gce_instance
| metric 'agent.googleapis.com/agent/uptime'
| align rate(4m)
| every 4m
  """,
  )
  unique_zones = set()
  # Fetch os inventory info for all VM instances by zones.
  for i in gce.get_instances(context).values():
    unique_zones.add(i.zone)
  for zone in unique_zones:
    osconfig.list_inventories(context, zone)

  # Fetch logs from syslog, windows event log, and ops agent health log.
  now = datetime.now(timezone.utc)
  # We need log entries within the past 20-minute timeframe.
  start_time = now - timedelta(minutes=20)
  time_filter = (
      f'timestamp>="{start_time.isoformat(timespec="seconds")}" AND timestamp'
      f' <= "{now.isoformat(timespec="seconds")}"')
  _syslog_query[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='gce_instance',
      log_name=f'projects/{context.project_id}/logs/syslog',
      filter_str=time_filter,
  )

  _windows_event_log_query[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='gce_instance',
      log_name=f'projects/{context.project_id}/logs/windows_event_log',
      filter_str=time_filter,
  )
  # we retrieve only the 'LogPing' entries from Ops Agent health log.
  _health_log_query[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='gce_instance',
      log_name=f'projects/{context.project_id}/logs/ops-agent-health',
      filter_str='"LogPingOpsAgent" AND ' + time_filter,
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Fetch all GCE VM instances from the inspected project.
  instances = list(gce.get_instances(context).values())
  if not instances:
    report.add_skipped(
        None, f'No VM instances found in project: {context.project_id}.')
    return

  instances = [
      Instance(context.project_id, i)
      for i in sorted(instances, key=op.attrgetter('project_id', 'full_path'))
  ]

  confirm_agent_installation_via_os_config(context, report, instances)
  confirm_agent_installation_via_uptime_metrics(context, report, instances)
  log_entries = format_log_entries(
      _syslog_query[context.project_id].entries,
      _windows_event_log_query[context.project_id].entries,
      _health_log_query[context.project_id].entries,
  )

  uptime_metric_entries = format_metric_entries(
      _query_results_project_id[context.project_id])
  populate_sub_agents_uptime_metrics_status(instances, uptime_metric_entries)
  populate_log_type_status(instances, log_entries)
  confirm_agent_telemetry_transmission(report, instances)


def confirm_agent_installation_via_os_config(
    context: models.Context,
    report: lint.LintReportRuleInterface,
    instances: List[Instance],
):
  unique_zones = set()
  for i in instances:
    unique_zones.add(i.zone)

  inventories: Dict[str, osconfig.Inventory] = {}
  for zone in unique_zones:
    inventories.update(osconfig.list_inventories(context, zone))

  for i in sorted(instances, key=op.attrgetter('project_id', 'name')):
    if i.is_gke_node:
      continue

    inventory = inventories.get(i.id)
    if inventory is None:
      i.has_os_inventory = False
      continue

    i.has_os_inventory = True
    for pkg_name in inventory.installed_packages:
      if OPS_AGENT_PACKAGE_NAME in pkg_name:
        i.ops_agent_installed = True
        break
    if not i.ops_agent_installed:
      report.add_failed(
          i.gce_instance,
          '',
          OPS_AGENT_NOT_INSTALLED_TEXT,
      )


def format_metric_entries(
    query_entry: monitoring.TimeSeriesCollection,) -> Dict[str, List[str]]:
  formatted_query_entries: Dict[str, List[str]] = {}
  for e in query_entry.values():
    try:
      instance_id = e['labels']['resource.instance_id']
      metric_version = e['labels']['metric.version']
      if instance_id in formatted_query_entries:
        formatted_query_entries[instance_id].append(metric_version)
      else:
        formatted_query_entries[instance_id] = [metric_version]
    except KeyError:
      logging.warning(
          'query entry without required label:resource.instance_id,'
          ' metric.version: %s',
          e,
      )
  return formatted_query_entries


def confirm_agent_installation_via_uptime_metrics(
    context: models.Context,
    report: lint.LintReportRuleInterface,
    instances: List[Instance],
):
  # Fetch Agent Uptime metrics.
  query = _query_results_project_id[context.project_id]
  try:
    vms_agents: Dict[str, List[str]] = {}
    for e in query.values():
      instance_id = e['labels']['resource.instance_id']
      metric_version = e['labels']['metric.version']
      if instance_id in vms_agents:
        vms_agents[instance_id].append(metric_version)
      else:
        vms_agents[instance_id] = [metric_version]
  except KeyError:
    for i in instances:
      if not i.has_os_inventory:
        report.add_skipped(
            i.gce_instance,
            UNABLE_TO_DETECT_EXPLANATION,
            OPS_AGENT_UNDETECTABLE_TEXT,
        )
    return

  # Verify Ops Agent installation for VMs that don't have OS Inventory.
  for i in sorted(
      instances,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.is_gke_node:
      continue
    # Skip VMs with confirmed Ops Agent installations via OS Config API.
    if i.has_os_inventory:
      continue
    if i.id in vms_agents:
      for metric_version in vms_agents[i.id]:
        if OPS_AGENT_PACKAGE_NAME in metric_version:
          i.ops_agent_installed = True
          break
      if not i.ops_agent_installed:
        report.add_failed(
            i.gce_instance,
            '',
            OPS_AGENT_NOT_INSTALLED_TEXT,
        )
    else:
      report.add_skipped(
          i.gce_instance,
          UNABLE_TO_DETECT_EXPLANATION,
          OPS_AGENT_UNDETECTABLE_TEXT,
      )


def populate_sub_agents_uptime_metrics_status(
    instances: List[Instance], formatted_metrics_entry: Dict[str, List[str]]):
  for i in sorted(
      instances,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.is_gke_node:
      continue
    if not i.ops_agent_installed:
      continue
    if i.id not in formatted_metrics_entry:
      continue
    for metric_version in formatted_metrics_entry[i.id]:
      if OPS_AGENT_LOGGING_METRICS_VERSION in metric_version:
        i.has_logging_uptime_metrics = True
      if OPS_AGENT_MONITORING_METRICS_VERSION in metric_version:
        i.has_monitoring_uptime_metrics = True


def populate_log_type_status(instances: List[Instance],
                             formatted_log_entry: Dict[str, Dict[str, bool]]):
  for i in sorted(
      instances,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.id in formatted_log_entry:
      e = formatted_log_entry[i.id]
      i.has_recent_log_pings = 'logPing' in e
      i.has_recent_log_entries = ('syslog' in e) or ('windowsEventLog' in e)
    else:
      i.has_recent_log_pings = False
      i.has_recent_log_entries = False


def format_log_entries(
    syslog_entries: Sequence,
    windows_event_log_entries: Sequence,
    agent_health_log_entries: Sequence,
) -> Dict[str, Dict[str, bool]]:
  formatted_log_entry: Dict[str, Dict[str, bool]] = {}
  for e in syslog_entries:
    try:
      instance_id = e['resource']['labels']['instance_id']
      if instance_id not in formatted_log_entry:
        formatted_log_entry[instance_id] = {}
      formatted_log_entry[instance_id]['syslog'] = True
    except KeyError:
      logging.warning('log entry without instance_id label: %s', e)

  for e in agent_health_log_entries:
    try:
      text_payload = e['jsonPayload']['code']
      if text_payload.lower() != 'logpingopsagent':
        continue
      instance_id = e['resource']['labels']['instance_id']
      if instance_id not in formatted_log_entry:
        formatted_log_entry[instance_id] = {}
      formatted_log_entry[instance_id]['logPing'] = True
    except KeyError:
      logging.warning(
          'log entry does not have required keys: jsonPayload.code and'
          ' resource.labels.instance_id: %s',
          e,
      )

  for e in windows_event_log_entries:
    try:
      instance_id = e['resource']['labels']['instance_id']
      if instance_id not in formatted_log_entry:
        formatted_log_entry[instance_id] = {}
      formatted_log_entry[instance_id]['windowsEventLog'] = True
    except KeyError:
      logging.warning('windows event log entry without instance_id label: %s',
                      e)
  return formatted_log_entry


def confirm_agent_telemetry_transmission(
    report: lint.LintReportRuleInterface,
    instances: List[Instance],
):
  # For all VMs with Ops Agent installed, verify both subagents are transmitting
  # telemetry.
  for i in sorted(
      instances,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.is_gke_node:
      continue
    if not i.ops_agent_installed:
      continue
    logging_subagent_up = (i.has_recent_log_pings) or (
        i.has_recent_log_entries and i.has_logging_uptime_metrics)
    monitoring_subagent_up = i.has_monitoring_uptime_metrics
    if logging_subagent_up and monitoring_subagent_up:
      report.add_ok(
          i.gce_instance,
          OPS_AGENT_OK_TEXT,
      )
    else:
      logging_subagent_up_text = 'Yes' if logging_subagent_up else 'No'
      monitoring_subagent_up_text = 'Yes' if monitoring_subagent_up else 'No'
      report.add_failed(
          i.gce_instance,
          OPS_AGENT_FAILS_TO_SEND_TELEMETRY_EXPLANATION % (
              logging_subagent_up_text,
              monitoring_subagent_up_text,
          ),
          OPS_AGENT_FAILS_TO_SEND_TELEMETRY_TEXT,
      )
