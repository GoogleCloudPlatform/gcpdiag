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
"""GCE VM instances don't have legacy Monitoring Agent installed.

Verify that GCE VMs in this project do not have the legacy Monitoring Agent
installed. Please uninstall the legacy Monitoring Agent from any VMs where it's
detected and install the Ops Agent.

To uninstall legacy Monitoring Agent, please follow:
https://cloud.google.com/monitoring/agent/monitoring/installation#uninstall.

To install the latest version of Ops Agent, please follow:
https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/installation#install-latest-version.
"""

import operator as op
from datetime import datetime, timedelta
from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, monitoring, osconfig

_query_results_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}

INSTANCE_MIN_AGE = timedelta(hours=1)
LEGACY_MONITORING_AGENT_PACKAGE_NAME = 'stackdriver-agent'
LEGACY_MONITORING_AGENT_METRICS_LABEL = 'stackdriver_agent'


def prefetch_rule(context: models.Context):
  _query_results_project_id[context.project_id] = monitoring.query(
      context.project_id,
      """
fetch gce_instance
| metric 'agent.googleapis.com/agent/uptime'
| align rate(4m)
| every 4m
  """,
  )
  # Fetch os inventory info for all VM instances.
  for i in gce.get_instances(context).values():
    osconfig.get_inventory(context, i.zone, i.name)

  crm.get_project(context.project_id)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = list(gce.get_instances(context).values())
  if not instances:
    report.add_skipped(
        None, f'No VM instances found in project: {context.project_id}.')
    return

  instances_without_osinventory = []
  all_ok = True
  for i in sorted(instances, key=op.attrgetter('project_id', 'name')):
    if i.is_gke_node():
      continue
    inventory = osconfig.get_inventory(context, i.zone, i.name)
    if inventory is None:
      instances_without_osinventory.append(i)
      continue
    for pkg_name in inventory.installed_packages:
      if LEGACY_MONITORING_AGENT_PACKAGE_NAME in pkg_name:
        report.add_failed(
            i,
            f'Legacy Monitoring Agent installed on VM: {i.name} in zone:'
            f' {i.zone}.',
            'Legacy Monitoring Agent present on the VM',
        )
        all_ok = False
        break

  query = _query_results_project_id[context.project_id]
  try:
    vms_agents = {
        e['labels']['resource.instance_id']: e['labels']['metric.version']
        for e in query.values()
    }
  except KeyError:
    for i in instances_without_osinventory:
      report.add_skipped(
          i,
          'Unable to confirm the presence of legacy Monitoring Agent on the'
          f' VM: {i.name}, in zone: {i.zone}.\n'
          'Please enable OS Config API: '
          'https://cloud.google.com/compute/docs/manage-os#enable-service-api'
          ' on your project and run the rule again.',
          'Not able to detect legacy Monitoring Agent',
      )
    return

  for i in sorted(
      instances_without_osinventory,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.is_gke_node():
      continue
    if datetime.utcnow() - i.creation_timestamp < INSTANCE_MIN_AGE:
      # instance is less than 1 hour of creation agent data might not be accurate yet
      report.add_skipped(
          i,
          'Unable to confirm the presence of legacy Monitoring Agent on'
          f' recently created VM: {i.name}, in zone: {i.zone}.',
          'Not able to detect legacy Monitoring Agent',
      )
      continue
    if i.id in vms_agents:
      if LEGACY_MONITORING_AGENT_METRICS_LABEL in vms_agents[i.id]:
        report.add_failed(
            i,
            f'Legacy Monitoring Agent installed on VM: {i.name} in zone:'
            f' {i.zone}.',
            'Legacy Monitoring Agent present on the VM',
        )
        all_ok = False
    else:
      all_ok = False
      report.add_skipped(
          i,
          'Unable to confirm the presence of legacy Monitoring Agent on the'
          f' VM: {i.name}, in zone: {i.zone}.\n'
          'Please enable OS Config API: '
          'https://cloud.google.com/compute/docs/manage-os#enable-service-api'
          ' on your project and run the rule again.',
          'Not able to detect legacy Monitoring Agent',
      )

  if all_ok:
    project = crm.get_project(context.project_id)
    report.add_ok(project)
