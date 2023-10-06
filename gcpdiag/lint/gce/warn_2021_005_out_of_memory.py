#
# Copyright 2021 Google LLC
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

# Lint as: python3
"""Serial logs don't contain out-of-memory messages

The messages:
"Out of memory: Kill process" / "sacrifice child" / "Killed process" /
"Memory cgroup out of memory" in serial output usually indicate that
a Linux instance is under memory pressure.
"""
from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce
from gcpdiag.queries.logs import LogEntryShort

OOM_MESSAGES = [
    'Out of memory: Kill process',  #
    'sacrifice child',
    'Killed process',
    'Memory cgroup out of memory'
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = utils.SerialOutputSearch(
      context, search_strings=OOM_MESSAGES)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule if serial outputs are unavailable
  if not utils.is_serial_port_one_logs_available(context):
    report.add_skipped(None, 'serial port output is unavailable')
    return

  search = logs_by_project[context.project_id]

  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
  else:
    for instance in sorted(instances, key=lambda i: i.name):
      match: Optional[LogEntryShort] = search.get_last_match(
          instance_id=instance.id)
      if match:
        report.add_failed(instance,
                          ('There are messages indicating that OS is running'
                           ' out of memory for {}\n{}: "{}"').format(
                               instance.name, match.timestamp_iso, match.text))
      else:
        report.add_ok(instance)
