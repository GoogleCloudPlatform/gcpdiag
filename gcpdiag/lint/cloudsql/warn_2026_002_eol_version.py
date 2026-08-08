# Copyright 2026 Google LLC
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
"""Cloud SQL instances are not running on EOL versions

Check if any Cloud SQL instance is running on a major version that has reached
its end of support or deprecation date.
"""

from datetime import date
from typing import Optional

from gcpdiag import lint, models
from gcpdiag.queries import cloudsql


def _check_version_eol(version: str, schedule: Optional[dict], today: date) -> tuple[bool, str]:
  if not schedule:
    known_eol = [
      'MYSQL_5_6',
      'MYSQL_5_7',
      'POSTGRES_9_6',
      'POSTGRES_10',
      'POSTGRES_11',
    ]
    if version in known_eol:
      return (
        True,
        f'Instance is running on {version} which is known to be End of Life.',
      )
    return False, ''

  regular_support_end = schedule.get('regular_support_end')
  extended_support_end = schedule.get('extended_support_end')

  if extended_support_end and today > extended_support_end:
    return (
      True,
      (
        f'Instance is running on {version} which has reached'
        f' Deprecation/End of Extended Support on {extended_support_end}.'
      ),
    )
  if regular_support_end and today > regular_support_end:
    return (
      True,
      (
        f'Instance is running on {version} which has reached End of Regular'
        f' Support on {regular_support_end}. It is in Extended Support.'
      ),
    )

  return False, ''


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = cloudsql.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')
    return

  release_schedule = cloudsql.get_release_schedule() or {}

  for instance in instances:
    version = instance.version
    schedule = release_schedule.get(version)
    is_eol, message = _check_version_eol(version, schedule, date.today())
    if is_eol:
      report.add_failed(instance, message)
    else:
      report.add_ok(instance)
