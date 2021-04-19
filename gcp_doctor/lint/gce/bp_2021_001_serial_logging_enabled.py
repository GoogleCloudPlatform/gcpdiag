# Lint as: python3
"""Serial port Cloud Logging is enabled.

Serial port output can be often useful for troubleshooting, and enabling serial
logging makes sure that you don't lose the information when the VM is rebooted.

Reference:
  https://cloud.google.com/compute/docs/instances/viewing-serial-port-output
"""

import operator as op

from gcp_doctor import lint, models
from gcp_doctor.queries import gce


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(), key=op.attrgetter('project_id', 'name')):
    # GKE nodes are checked by another test.
    if i.is_gke_node():
      continue
    instances_count += 1
    if i.is_serial_port_logging_enabled():
      report.add_ok(i)
    else:
      report.add_failed(i, 'serial port Cloud Logging isn\'t enabled')
  if not instances_count:
    report.add_skipped(None, 'no instances found')
