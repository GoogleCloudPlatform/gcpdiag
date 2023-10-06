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
"""Serial logs don't contain Guest OS activation errors

Premium Guest OSes need to activate their license when created and
refreshed regularly after activation. In an event that guest OS cannot
communicate with the license servers, the messages:
"Could not contact activation server." /
"Server needs to be activated by a KMS Server" /
"Exiting without registration" in the serial output would
indicate license activation failures.
"""

from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce
from gcpdiag.queries.logs import LogEntryShort

GUEST_OS_ACTIVATION_ERR_MESSAGES = [
    'needs to be activated by a KMS Server',  # Windows
    'Could not contact activation server. Will retry activation later',
    'Exiting without registration'  # SLES
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = utils.SerialOutputSearch(
      context, search_strings=GUEST_OS_ACTIVATION_ERR_MESSAGES)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule if serial outputs are unavailable
  if not utils.is_serial_port_one_logs_available(context):
    report.add_skipped(None, 'serial port output is unavailable')
    return

  search = logs_by_project[context.project_id]

  instances = gce.get_instances(context).values()
  if not instances:
    report.add_skipped(None, 'no instances found')
  for instance in sorted(instances, key=lambda i: i.name):
    # this lint rule isn't relevant to GKE nodes
    if instance.is_gke_node():
      continue

    match: Optional[LogEntryShort] = search.get_last_match(
        instance_id=instance.id)
    if match:
      report.add_failed(
          instance,
          f'There are messages indicating that {instance.name} can\'t be activated: '
          f'{match.text}')
    else:
      report.add_ok(instance)
