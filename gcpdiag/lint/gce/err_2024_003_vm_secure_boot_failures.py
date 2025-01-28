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
""" GCE Shielded VM secure boot validations

Identifies if Shielded VMs are facing boot issues due to Secure boot
configurations or if there are Secure boot related fail events in
cloud logging.
"""

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce

shutdown_logs: utils.QueryCloudLogs
boot_fail_event: utils.SerialOutputSearch


def prepare_rule(context: models.Context):
  # Fetching the list of instances in the project
  resource_type = 'gce_instance'
  filter_log = ['severity=ERROR']
  logid = ['compute.googleapis.com%2Fshielded_vm_integrity']
  global shutdown_logs
  shutdown_logs = utils.QueryCloudLogs(context.project_id, resource_type,
                                       filter_log, logid)

  boot_fail_str = [
      'Failed to start image', 'Failed to load image',
      'Verification failed: (0x1A) Security Violation', 'Binary is blacklisted'
  ]

  global boot_fail_event
  boot_fail_event = utils.SerialOutputSearch(context,
                                             search_strings=boot_fail_str)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Analyzing logs for all the instances
  instances = gce.get_instances(context).values()
  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  for i in sorted(instances):
    if i.secure_boot_enabled():
      temp = None
      if shutdown_logs:
        temp = shutdown_logs.get_entries(i.id).values()
      if temp:
        for log_entry in temp:
          earlybootreportevent: str = ''
          latebootreportevent: str = ''
          earlybootreportevent = get_path(
              log_entry,
              ('jsonPayload', 'earlyBootReportEvent', 'policyEvaluationPassed'),
              default='')
          latebootreportevent = get_path(
              log_entry,
              ('jsonPayload', 'lateBootReportEvent', 'policyEvaluationPassed'),
              default='')

          if earlybootreportevent is False or latebootreportevent is False:
            if (i.startrestricted is True) or (boot_fail_event.get_last_match(
                i.id)):
              report.add_failed(
                  i,
                  'Instance has been restricted to boot due to Shielded VM policy violations'
              )
            else:
              report.add_failed(
                  i, 'Instance is Shielded VM, has Secure boot failures events')
      else:
        report.add_ok(i)
    else:
      report.add_skipped(i, reason='Secure Boot is disabled for the instance')
