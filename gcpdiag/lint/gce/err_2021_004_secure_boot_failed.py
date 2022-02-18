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
"""Serial logs don't contain Secure Boot error messages

The messages: "Security Violation" / "Binary is blacklisted" /
"UEFI: Failed to start image" / "UEFI: Failed to load image"
in serial output usually indicate that the Secure Boot doesn't pass its
pre-checks.
"""

from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.gce.utils import LogEntryShort, SerialOutputSearch
from gcpdiag.queries import apis, gce

SECURE_BOOT_ERR_MESSAGES = [
    'UEFI: Failed to load image.',  #
    'UEFI: Failed to start image.',
    'Status: Security Violation',
    'Binary is blacklisted ',
    'Verification failed: (0x1A) Security Violation',
]

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = SerialOutputSearch(
      context, search_strings=SECURE_BOOT_ERR_MESSAGES)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  search = logs_by_project[context.project_id]

  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
  for instance in sorted(instances, key=lambda i: i.name):
    # this lint rule isn't relevant to GKE nodes
    if instance.is_gke_node():
      continue

    match: Optional[LogEntryShort] = search.get_last_match(
        instance_id=instance.id)
    if match:
      report.add_failed(
          instance,
          ('There are messages indicating that the Secure Boot violations'
           ' prevent booting {}\n{}: "{}"').format(instance.name,
                                                   match.timestamp_iso,
                                                   match.text))
    else:
      report.add_ok(instance)
