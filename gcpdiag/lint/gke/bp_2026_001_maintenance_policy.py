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
"""GKE maintenance policy is valid and sufficient.

Check that the maintenance window is configured, not expired, and has a
reasonable duration.
"""

import re
from datetime import datetime, timedelta, timezone

import dateutil.parser
from dateutil.rrule import rrulestr

from gcpdiag import lint, models
from gcpdiag.queries import gke

clusters_by_project = {}


def prepare_rule(context: models.Context):
  clusters_by_project[context.project_id] = gke.get_clusters(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  for _, c in sorted(clusters.items()):
    if not c.has_maintenance_window():
      report.add_failed(c, 'does not have maintenance window configured')
      continue

    policy = c.maintenance_policy
    window = policy.get('window', {})

    # Check for recurring window
    recurring = window.get('recurringWindow', {})
    if recurring:
      recurrence = recurring.get('recurrence', '')
      time_window = recurring.get('window', {})
      start_time_str = time_window.get('startTime')
      end_time_str = time_window.get('endTime')

      # Check expiration (UNTIL in RULE)
      until_match = re.search(r'UNTIL=(\d{8}T\d{6}Z)', recurrence)
      if until_match:
        until_str = until_match.group(1)
        until_dt = datetime.strptime(until_str, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        if until_dt < datetime.now(timezone.utc):
          report.add_failed(c, f'maintenance window expired on {until_dt}')
          continue

      # Calculate total duration in a 32-day rolling window
      if start_time_str and end_time_str:
        start_dt = dateutil.parser.isoparse(start_time_str)
        if start_dt.tzinfo is None:
          start_dt = start_dt.replace(tzinfo=timezone.utc)
        end_dt = dateutil.parser.isoparse(end_time_str)
        if end_dt.tzinfo is None:
          end_dt = end_dt.replace(tzinfo=timezone.utc)
        single_duration = end_dt - start_dt

        try:
          rule = rrulestr(recurrence, dtstart=start_dt)
          now = datetime.now(timezone.utc)
          occurrences = rule.between(now, now + timedelta(days=32))
          total_hours = (len(occurrences) * single_duration.total_seconds()) / 3600

          if total_hours < 48:
            report.add_failed(
              c,
              'maintenance window availability is too short:'
              f' {total_hours:.2f} hours in 32 days (required >= 48h)',
            )
            continue
        except Exception:
          # Fallback if rrule parsing fails
          if single_duration.total_seconds() < 4 * 3600:
            report.add_failed(
              c,
              'maintenance window duration is too short:'
              f' {single_duration.total_seconds() / 3600:.2f} hours'
              ' (recommended >= 4h)',
            )
            continue

    # Check for daily window (legacy)
    daily = window.get('dailyMaintenanceWindow', {})
    if daily:
      duration_str = daily.get('duration', '')
      seconds = 0.0
      if duration_str.endswith('s'):
        seconds = float(duration_str[:-1])
      elif duration_str.endswith('h'):
        seconds = float(duration_str[:-1]) * 3600

      total_hours = (seconds * 32) / 3600
      if total_hours < 48:
        report.add_failed(
          c,
          'daily maintenance window availability is too short:'
          f' {total_hours:.2f} hours in 32 days (required >= 48h)',
        )
        continue

    report.add_ok(c)
