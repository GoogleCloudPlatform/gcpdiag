# Copyright 2022 Google LLC
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
"""Vertex AI Workbench instance is not being OOMKilled

High memory utilization more than 85% in the user-managed notebooks instance
could be a cause of 524 (A Timeout Occurred) errors while opening Jupyterlab.
"""
import re

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import apis, gce, notebooks

OOMKILLED_MESSAGES = [
    'Out of memory: Kill process', 'oom_reaper: reaped process'
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = utils.SerialOutputSearch(
      context, search_strings=OOMKILLED_MESSAGES)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(None, 'Notebooks API is disabled')
    return

  instances = notebooks.get_instances(context)
  if not instances:
    report.add_skipped(None, 'No instances found')
    return

  if not utils.is_serial_port_one_logs_available(context):
    report.add_skipped(None, 'serial port output is unavailable')
    return

  search = logs_by_project[context.project_id]
  p_gce_vm = re.compile(r'projects/.+/locations/(.+)/instances/(.+)')

  for instance in instances.values():
    result = p_gce_vm.match(instance.name)
    if not result:
      continue

    zone, vm_name = result.group(1), result.group(2)
    gce_vm = gce.get_instance(context.project_id, zone, vm_name)

    if search.get_last_match(instance_id=gce_vm.id):
      report.add_failed(instance)
    else:
      report.add_ok(instance)
