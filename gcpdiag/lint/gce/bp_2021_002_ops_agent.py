# Copyright 2021 Google LLC
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
"""GCE nodes have an up to date ops agent installed.

Verify that the ops agent is used by the GCE instances
and that the agent is recent enough.
If the monitoring agent is found it is recommended to upgrade to the ops agent.

see: https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent
"""

import operator as op
from datetime import datetime, timedelta
from typing import Dict

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import gce, monitoring

_query_results_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}

INSTANCE_MIN_AGE = timedelta(hours=1)

OPS_NAME = 'google-cloud-ops-agent-metrics'
MONITORING_NAME = 'stackdriver_agent'
OPS_AGENT_MIN_VERSION = version.parse('2.6.0')


def prefetch_rule(context: models.Context):
  # Fetch the metrics for all instances.
  instances = [
      vm for vm in gce.get_instances(context).values() if not vm.is_gke_node()
  ]
  if not instances:
    return

  _query_results_project_id[context.project_id] = \
      monitoring.query(
          context.project_id, """
fetch gce_instance
| metric 'agent.googleapis.com/agent/uptime'
| align rate(4m)
| every 4m
  """)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = [
      vm for vm in gce.get_instances(context).values() if not vm.is_gke_node()
  ]
  if not instances:
    report.add_skipped(None, 'no instances found')
    return
  if not context.project_id in _query_results_project_id:
    report.add_skipped(None, 'no instances found')
    return
  query = _query_results_project_id[context.project_id]
  try:
    vms_agents = {
        e['labels']['resource.instance_id']: e['labels']['metric.version']
        for e in query.values()
    }
  except KeyError:
    report.add_skipped(None, 'The metrics have incorrect labels')
  for i in sorted(instances, key=op.attrgetter('project_id', 'name')):
    if datetime.utcnow() - i.creation_timestamp < INSTANCE_MIN_AGE:
      #instance is less than 1 hour of creation agent data might not be accurate yet
      continue
    if i.id in vms_agents:
      if MONITORING_NAME in vms_agents[i.id]:
        report.add_failed(
            i,
            'instance using old monitoring agent instead of ops agent. See description to upgrade'
        )
      if OPS_NAME in vms_agents[i.id]:
        if OPS_AGENT_MIN_VERSION <= version.parse(
            vms_agents[i.id].split('/')[1].split('-')[0]):
          report.add_ok(i)
        else:
          # if an unsafe or buggy old version is present
          # we notify the user here by changing to add fail
          report.add_failed(
              i,
              f'ops agent too old, should be at least ({OPS_AGENT_MIN_VERSION})'
          )
    else:
      report.add_failed(i, 'ops agent not installed.')
