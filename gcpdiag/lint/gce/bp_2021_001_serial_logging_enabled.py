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

# Lint as: python3
"""Serial port logging is enabled.

Serial port output can be often useful for troubleshooting, and enabling serial
logging makes sure that you don't lose the information when the VM is restarted.
Additionally, serial port logs are timestamped, which is useful to determine
when a particular serial output line was printed.

Reference:
  https://cloud.google.com/compute/docs/instances/viewing-serial-port-output
"""

import operator as op

from gcpdiag import lint, models
from gcpdiag.queries import gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(), key=op.attrgetter('project_id', 'name')):
    instances_count += 1
    if i.is_serial_port_logging_enabled():
      report.add_ok(i)
    else:
      report.add_failed(i)
  if not instances_count:
    report.add_skipped(None, 'no instances found')
