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
"""GCE CPU quota is not near the limit.

CPU quota is a regional quota and limits the number of CPU
that can exist in a given region.

Rule will start failing if quota usage will be higher then configured threshold (80%).
"""

from typing import Dict

from gcpdiag import config, lint, models
from gcpdiag.queries import gce, monitoring, quotas

GCE_SERVICE_NAME = 'compute.googleapis.com'
# name of the quota limit
QUOTA_LIMIT_NAME = '.*CPUS-per-project-region'
# name of the quota metric
QUOTA_METRIC_NAMES = (
    'compute.googleapis.com/cpus',
    'compute.googleapis.com/n2_cpus',
    'compute.googleapis.com/n2d_cpus',
    'compute.googleapis.com/m1_cpus',
    'compute.googleapis.com/m2_cpus',
    'compute.googleapis.com/c2_cpus',
    'compute.googleapis.com/a2_cpus',
    'compute.googleapis.com/c2d_cpus',
    'compute.googleapis.com/n2d_cpus',
    'compute.googleapis.com/t2d_cpus',
)
# percentage of the quota limit usage
QUOTA_LIMIT_THRESHOLD = 0.80
_query_results_per_project_id: Dict[str, monitoring.TimeSeriesCollection] = {}


def prefetch_rule(context: models.Context):

  # fetch the metrics if we have any instances
  regions_with_instances = gce.get_regions_with_instances(context)
  if not regions_with_instances:
    return

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
  regions_with_instances = gce.get_regions_with_instances(context)
  if not regions_with_instances:
    report.add_skipped(None, 'no instances found')
    return

  for region in sorted(regions_with_instances, key=lambda r: r.name):
    all_skipped = True
    for quota_metric_name in QUOTA_METRIC_NAMES:

      ts_key = frozenset({
          f'resource.project_id:{context.project_id}',
          f'metric.quota_metric:{quota_metric_name}',
          f'resource.location:{region.name}'
      })
      try:
        ts = _query_results_per_project_id[context.project_id][ts_key]
        all_skipped = False
      except KeyError:
        # silently skip
        continue

      # did we exceeded threshold on any day?
      exceeded = False
      for day_value in ts['values']:
        ratio = day_value[0]
        limit = day_value[1]
        if ratio > QUOTA_LIMIT_THRESHOLD:
          exceeded = True

      if exceeded:
        report.add_failed(region,
                          (f'Region has reached {ratio:.0%} of {limit} limit:\n'
                           f' quota metric: {quota_metric_name}'))
      else:
        report.add_ok(region)

    # report skip if all data for region not available
    if all_skipped:
      report.add_skipped(region, 'no data')
