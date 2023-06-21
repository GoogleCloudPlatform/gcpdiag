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
"""Cloud Composer's worker concurrency is not limited by parallelism parameter

The parallelism defines the maximum number of task instances that can run
concurrently in Airflow. Generally, the parameter should be equal or higher than
the product of maximum number of workers and worker_concurrency. Otherwise,
resources in workers could not be fully-utilized.
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
    if not env.is_composer2:
      report.add_skipped(env, 'not applicable for composer1')
      continue

    if env.parallelism < (env.worker_max_count * env.worker_concurrency):
      report.add_failed(env)
    else:
      report.add_ok(env)
