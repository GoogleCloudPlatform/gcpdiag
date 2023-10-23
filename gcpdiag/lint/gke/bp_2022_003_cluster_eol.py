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

from datetime import date, timedelta
from os.path import dirname
from typing import Dict

from boltons.iterutils import get_path
from yaml import safe_load

from gcpdiag import lint, models
from gcpdiag.queries import gke
from gcpdiag.utils import Version

# how many days before eol rule will start to failing
NOTIFY_PERIOD_IN_DAYS = 30
BASE_OSS_K8S_VERSION = Version('1.23')
BASE_OSS_K8S_RELEASE_DATE = date(2021, 12, 7)
FUTURE_OSS_K8S_RELEASE_DATE = date(2200, 1, 1)
MINOR_RELEASE_PACE_IN_DAYS = 122  # every 4 months
GKE_REGULAR_SUPPORT_PERIOD_IN_DAYS = 426  # 14 months
GKE_TIME_TO_RAPID_IN_DAYS = 30  # ~1 month
GKE_TIME_TO_REGULAR_IN_DAYS = 91  # ~3 months
TBD = 'TBD'


def _estimate_oss_release_date(version: Version) -> date:
  """
  Estimate a release date of K8s OSS for a given K8s version

  Since K8s v1.22 the release pace is 3 versions a year or every 4 month
  https://kubernetes.io/blog/2021/07/20/new-kubernetes-release-cadence/

  This function doesn't return a valid date for K8s versions older that v1.23.
  The precision of the functon is +-30days and could be bigger for v1.100+
  """
  # Return a date of already EOLed version for versions older than BASE_OSS_K8S_VERSION
  if version.major <= BASE_OSS_K8S_VERSION.major and version.minor <= BASE_OSS_K8S_VERSION.minor:
    return BASE_OSS_K8S_RELEASE_DATE
  # K8s v2 isn't planned at the moment
  if version.major > BASE_OSS_K8S_VERSION.major:
    return FUTURE_OSS_K8S_RELEASE_DATE
  # Calculate a possible release date
  return BASE_OSS_K8S_RELEASE_DATE + timedelta(
      days=(version.minor - BASE_OSS_K8S_VERSION.minor) *
      MINOR_RELEASE_PACE_IN_DAYS)


def _get_date(str_or_date) -> date:
  # Handle incomplete dates in 'YYYY-MM' form
  if str_or_date and isinstance(str_or_date,
                                str) and len(str_or_date) == len('YYYY-MM'):
    return date.fromisoformat(f'{str_or_date}-15')
  return str_or_date


def _estimate_gke_eol_date(version: Version, eol_schedule: Dict):
  """
  Estimate End Of Life date for a given GKE version

  After a OSS K8s version is released it hits GKE Rapid channel in ~30 days.
  It's being promoted to GKE Regular chennel in ~90 days.
  After a version hits Regular channel it's supported for 14 months.
  """

  short_version = f'{version.major}.{version.minor}'

  regular_release = _get_date(
      get_path(eol_schedule, (short_version, 'regular_avail'), None))
  rapid_release = _get_date(
      get_path(eol_schedule, (short_version, 'rapid_avail'), None))
  oss_release = _get_date(
      get_path(eol_schedule, (short_version, 'oss_release'), None))

  if regular_release and regular_release != TBD:
    return regular_release + timedelta(days=GKE_REGULAR_SUPPORT_PERIOD_IN_DAYS)
  if rapid_release and rapid_release != TBD:
    return rapid_release + timedelta(days=GKE_TIME_TO_REGULAR_IN_DAYS +
                                     GKE_REGULAR_SUPPORT_PERIOD_IN_DAYS)

  if oss_release and oss_release != TBD:
    base_oss_release = oss_release
  else:
    base_oss_release = _estimate_oss_release_date(version)
  return base_oss_release + timedelta(days=GKE_TIME_TO_RAPID_IN_DAYS +
                                      GKE_TIME_TO_REGULAR_IN_DAYS +
                                      GKE_REGULAR_SUPPORT_PERIOD_IN_DAYS)


def _notification_required(version: Version, eol_schedule: Dict) -> bool:
  """Validate if notification is required based on the static channel schedule"""

  short_version = f'{version.major}.{version.minor}'

  # Check if the version is older that the oldest version in the EOL file
  lowest_version = None
  if eol_schedule.keys():
    lowest_version = sorted(eol_schedule.keys())[0]
  if lowest_version and version < Version(lowest_version):
    eol_schedule[short_version] = {'eol': 'already reached EOL', 'eoled': True}
    return True

  if not eol_schedule or (short_version not in eol_schedule) or (
      eol_schedule[short_version]['eol'] == TBD):
    # The version is NOT defined in the static EOL versions file or is unknowd (TBD)
    eol_date = _estimate_gke_eol_date(version, eol_schedule)
    # Update the EOL date in the `eol_schedule` dict
    eol_schedule[short_version] = {'eol': eol_date, 'estimated': True}
  else:
    eol_date = _get_date(eol_schedule[short_version]['eol'])

  return date.today() > eol_date - timedelta(days=NOTIFY_PERIOD_IN_DAYS)


def _get_notification_msg(version: Version, eol_schedule: Dict) -> str:
  short_version = f'{version.major}.{version.minor}'
  msg = f'''GKE version {short_version}\n
    scheduled end of life: {_get_date(eol_schedule[short_version]["eol"])}'''
  if 'estimated' in eol_schedule[short_version]:
    msg += ' (estimation)'
  return msg


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # This file should be updated regularly by `eol_parser.sh` or by `make`:
  #  <root_prj_folder>$ make gke-eol-file
  try:
    with open(f'{dirname(__file__)}/eol.yaml', encoding='utf-8') as eol_file:
      eol_schedule = safe_load(eol_file)
  except OSError:
    # Ignore absence of the file, estimations will be used
    eol_schedule = {}

  for _, c in sorted(clusters.items()):
    if c.release_channel:
      report.add_skipped(c, 'release channel: ' + c.release_channel)
      continue
    if _notification_required(c.master_version, eol_schedule):
      report.add_failed(c, _get_notification_msg(c.master_version,
                                                 eol_schedule))
      continue
    for np in c.nodepools:
      if _notification_required(np.version, eol_schedule):
        report.add_failed(np, _get_notification_msg(np.version, eol_schedule))
      else:
        report.add_ok(np)
