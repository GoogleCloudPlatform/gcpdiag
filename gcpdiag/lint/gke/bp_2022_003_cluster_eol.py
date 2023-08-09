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
"""GKE cluster is not near to end of life

The GKE clusters should be updated regularly. It is recommended to keep your
GKE cluster version up to date and avoid reaching end of life.

Rule will start failing if scheduled end of life is in less than 30 days.
"""

from datetime import datetime, timedelta

from gcpdiag import lint, models
from gcpdiag.queries import gke

# this should be updated regularly from:
# https://cloud.google.com/kubernetes-engine/docs/release-schedule#schedule_for_static_no_channel_versions
EOL_SCHEDULE = {
    '1.21': datetime.strptime('2023-01-31', '%Y-%m-%d'),
    '1.22': datetime.strptime('2023-04-30', '%Y-%m-%d'),
    '1.23': datetime.strptime('2023-07-31', '%Y-%m-%d'),
    '1.24': datetime.strptime('2023-10-31', '%Y-%m-%d'),
    '1.25': datetime.strptime('2024-02-29', '%Y-%m-%d'),
    '1.26': datetime.strptime('2024-06-30', '%Y-%m-%d'),
    '1.27': datetime.strptime('2024-08-31', '%Y-%m-%d'),
}

# how many days before eol rule will start to failing
NOTIFY_PERIOD_IN_DAYS = 30


def _notification_required(version: str) -> bool:
  """Validate if notification is required based on the static channel schedule"""
  eol_date = EOL_SCHEDULE.get(version)
  if eol_date and (datetime.now() <
                   eol_date - timedelta(days=NOTIFY_PERIOD_IN_DAYS)):
    return False
  return True


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    if c.release_channel:
      report.add_skipped(c, 'release channel: ' + c.release_channel)
      continue
    master_ver = f'{c.master_version.major}.{c.master_version.minor}'
    if _notification_required(master_ver):
      report.add_failed(c, (f'cluster version: {master_ver}\n'
                            'scheduled end of life: '
                            f'{EOL_SCHEDULE.get(master_ver, "EOL")}'))
      continue
    for np in c.nodepools:
      node_ver = f'{np.version.major}.{np.version.minor}'

      if _notification_required(node_ver):
        report.add_failed(np, (f'node pool version: {node_ver}\n'
                               'scheduled end of life: '
                               f'{EOL_SCHEDULE.get(node_ver, "EOL")}'))
      else:
        report.add_ok(np)
