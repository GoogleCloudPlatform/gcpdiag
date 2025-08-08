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
"""Instance time source is configured with Google NTP server

Google recommends Compute Engine instances to be configured with
Google NTP servers to facilitate reliable time sync. Google can't predict how
external NTP services behave. If at all possible, it is recommended that you do
not use external NTP sources with Compute Engine virtual machines.
"""

from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce
from gcpdiag.queries.logs import LogEntryShort

NTP_TIME_SYNC_MESSAGES = ['Time synchronized with', 'Selected source']
RECOMMENDED_NTP_SERVERS = [
    'metadata.google.internal', '169.254.169.254', 'metadata.google'
]
logs_by_project = {}


def prepare_rule(context: models.Context):
  filter_str = '''textPayload:("chronyd" OR "ntpd")
   AND ("Selected source" OR "Time synchronized with")'''
  logs_by_project[context.project_id] = utils.SerialOutputSearch(
      context, search_strings=NTP_TIME_SYNC_MESSAGES, custom_filter=filter_str)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule if serial outputs are unavailable
  if not utils.is_serial_port_one_logs_available(context):
    report.add_skipped(None, 'serial port output is unavailable')
    return

  search = logs_by_project[context.project_id]

  instances = gce.get_instances(context).values()

  if instances:
    for instance in sorted(instances, key=lambda i: i.name):
      match: Optional[LogEntryShort] = search.get_last_match(
          instance_id=instance.id)
      if not match:
        report.add_skipped(instance, 'No indication of NTP Service time sync')
      elif not any(server in match.text for server in RECOMMENDED_NTP_SERVERS):
        report.add_failed(instance, (f"{match.text.split(']:')[1][:-4]}"
                                     'is not a GCP recommended NTP server'))
      else:
        report.add_ok(instance)
  else:
    report.add_skipped(None, 'No instances found')
