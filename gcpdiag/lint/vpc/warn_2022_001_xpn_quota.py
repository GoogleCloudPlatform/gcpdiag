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
"""Cross Project Networking Service projects quota is not near the limit.

Cross Project Networking Service projects quota is a global quota that limits the number
of service projects one can have for a given host project.

Rule will start failing if quota usage will be higher than 80%.
"""

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import crm, gce, monitoring, quotas

GCE_SERVICE_NAME = 'compute.googleapis.com'
# name of the quota limit
QUOTA_LIMIT_NAME = 'XPN-SERVICE-PROJECTS-per-project'
# name of the quota metric
QUOTA_METRIC_NAMES = 'compute.googleapis.com/xpn_service_projects'
# percentage of the quota limit usage
QUOTA_LIMIT_THRESHOLD = 0.80
_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):

  params = {
      'service_name': GCE_SERVICE_NAME,
      'limit_name': QUOTA_LIMIT_NAME,
      'within_days': config.get('within_days')
  }
  _query_results_per_project_id[context.project_id] = \
      monitoring.query(
          context.project_id,
          quotas.CONSUMER_QUOTA_QUERY_TEMPLATE.format_map(params))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  region = gce.Region(context.project_id, {'name': 'global', 'selfLink': ''})
  #set region to global

  ts_key = frozenset({
      f'resource.project_id:{context.project_id}',
      f'metric.quota_metric:{QUOTA_METRIC_NAMES}',
      f'resource.location:{region.name}'
  })
  try:
    ts = _query_results_per_project_id[context.project_id][ts_key]
  except KeyError:
    report.add_skipped(project, 'no data')
    return

  # did we exceeded threshold on any day?
  exceeded = False
  for day_value in ts['values']:
    ratio = day_value[0]
    limit = day_value[1]
    if ratio > QUOTA_LIMIT_THRESHOLD:
      exceeded = True
  if exceeded:
    report.add_failed(project,
                      (f'Project has reached {ratio:.0%} of {limit} limit:\n'
                       f' quota metric: {QUOTA_METRIC_NAMES}'))
  else:
    report.add_ok(project, f' quota metric: {QUOTA_METRIC_NAMES}')
