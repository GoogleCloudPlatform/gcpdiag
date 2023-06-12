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
"""Cloud Composer has no more than 2 Airflow schedulers

In general, extra schedulers more than 2 consumes resources of your environment
without contributing to overall performance. We recommend starting with two
schedulers and then monitoring the performance of your environment.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, composer

envs_by_project = {}


def prefetch_rule(context: models.Context):
  envs_by_project[context.project_id] = composer.get_environments(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'composer'):
    report.add_skipped(None, 'composer is disabled')
    return

  envs = envs_by_project[context.project_id]

  if not envs:
    report.add_skipped(None, 'no Cloud Composer environments found')
    return

  for env in envs:
    if env.num_schedulers > 2:
      report.add_failed(
          env, f'{env.name} is configured more than 2 Airflow schedulers'
          ' (number_of_schedulers: {env.num_schedulers})')
    else:
      report.add_ok(env)
