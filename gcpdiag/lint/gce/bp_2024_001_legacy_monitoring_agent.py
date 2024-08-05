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
"""Verify that GCE VM Instances Don't Have Legacy Monitoring Agent Installed.

Please uninstall the legacy monitoring agent from any VMs where it's
detected and install the Ops Agent.

To uninstall legacy monitoring agent, please follow:
https://cloud.google.com/monitoring/agent/monitoring/installation#uninstall.

To install the latest version of Ops Agent, please follow:
https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/installation#install-latest-version.
"""

import operator as op
from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gce, monitoring, osconfig

_query_results_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}

LEGACY_MONITORING_AGENT_PACKAGE_NAME = 'stackdriver-agent'
LEGACY_MONITORING_AGENT_METRICS_LABEL = 'stackdriver_agent'
LEGACY_AGENT_NOT_DETECTED = 'Legacy monitoring agent not installed on the VM'
UNABLE_TO_DETECT = 'Unable to confirm legacy monitoring agent installation'
UNABLE_TO_DETECT_EXPLANATION = (
    'VM Manager is needed for the legacy agent detection. Please enable it at:'
    ' https://cloud.google.com/compute/docs/manage-os#automatic and run this'
    ' check again.')
LEGACY_AGENT_DETECTED = 'Legacy monitoring agent installed on the VM'


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


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = list(gce.get_instances(context).values())
  if not instances:
    report.add_skipped(
        None, f'No VM instances found in project: {context.project_id}.')
    return

  instances_without_osinventory = []
  for i in sorted(instances, key=op.attrgetter('project_id', 'full_path')):
    if i.is_gke_node():
      continue
    inventory = osconfig.get_inventory(context, i.zone, i.name)
    if inventory is None:
      instances_without_osinventory.append(i)
      continue
    legacy_agent_found = False
    for pkg_name in inventory.installed_packages:
      if LEGACY_MONITORING_AGENT_PACKAGE_NAME in pkg_name:
        report.add_failed(
            i,
            '',
            LEGACY_AGENT_DETECTED,
        )
        legacy_agent_found = True
        break
    if not legacy_agent_found:
      report.add_ok(i, LEGACY_AGENT_NOT_DETECTED)

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
          UNABLE_TO_DETECT_EXPLANATION,
          UNABLE_TO_DETECT,
      )
    return

  for i in sorted(
      instances_without_osinventory,
      key=op.attrgetter('project_id', 'name'),
  ):
    if i.is_gke_node():
      continue
    if i.id in vms_agents:
      if LEGACY_MONITORING_AGENT_METRICS_LABEL in vms_agents[i.id]:
        report.add_failed(
            i,
            '',
            LEGACY_AGENT_DETECTED,
        )
      else:
        report.add_ok(i, LEGACY_AGENT_NOT_DETECTED)
    else:
      report.add_skipped(
          i,
          UNABLE_TO_DETECT_EXPLANATION,
          UNABLE_TO_DETECT,
      )
