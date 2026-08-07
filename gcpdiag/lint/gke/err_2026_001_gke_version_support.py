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
"""GKE cluster versions are kept up to date and supported.

GKE clusters should be updated regularly. Cluster versions must be kept up to
date
and not allowed to run past the end-of-life support dates.
This rule considers both Standard Support dates and Extended (LTS) Support dates
based on the configured release channel (RAPID, REGULAR, STABLE, EXTENDED).
"""

# Rule implementation for GKE cluster version support linter.
from datetime import date
from typing import Dict

from gcpdiag import lint, models
from gcpdiag.queries import gke
from gcpdiag.utils import Version


def _is_version_unsupported(version: Version, release_channel: str, eol_schedule: Dict) -> bool:
  short_version = f'{version.major}.{version.minor}'

  if not eol_schedule or short_version not in eol_schedule:
    # If it's completely missing, it might be either way too old, or way too new.
    # Older than the very first item in the schedule definitely means unsupported.
    if eol_schedule:
      lowest_version = sorted(eol_schedule.keys(), key=Version)[0]
      if version < Version(lowest_version):
        return True
    return False

  schedule = eol_schedule[short_version]

  # Determine effective EOL date based on release channel
  if release_channel == 'EXTENDED':
    effective_eol = schedule.get('extended_eol') or schedule.get('eol')
  else:
    effective_eol = schedule.get('eol')

  if not effective_eol or isinstance(effective_eol, str):
    # If TBD or string "already reached EOL", we fallback to False unless it explicitly states EOL
    if effective_eol == 'already reached EOL':
      return True
    return False

  return date.today() > effective_eol


def _get_notification_msg(version: Version, release_channel: str, eol_schedule: Dict) -> str:
  short_version = f'{version.major}.{version.minor}'
  schedule = eol_schedule.get(short_version, {})

  if not schedule:
    effective_eol = 'Unknown (Version too old)'
  elif release_channel == 'EXTENDED':
    effective_eol = schedule.get('extended_eol') or schedule.get('eol')
  else:
    effective_eol = schedule.get('eol')

  return (
    f'Version {short_version} is past its end of support: {effective_eol} '
    f'(Channel: {release_channel})'
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  eol_schedule = gke.get_release_schedule()

  for _, c in sorted(clusters.items()):
    channel = c.release_channel or 'UNSPECIFIED'

    # Check Control Plane version
    if _is_version_unsupported(c.master_version, channel, eol_schedule):
      report.add_failed(c, _get_notification_msg(c.master_version, channel, eol_schedule))
    else:
      report.add_ok(c)

    # Check Nodepools versions
    for np in c.nodepools:
      if _is_version_unsupported(np.version, channel, eol_schedule):
        report.add_failed(np, _get_notification_msg(np.version, channel, eol_schedule))
      else:
        report.add_ok(np)
