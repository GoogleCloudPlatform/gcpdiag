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
"""Cloud Composer is not in ERROR state

The ERROR state indicates that the environment has encountered an error and
cannot be used. Creating/updateing environment through misconfigured Terraform
config, errors in PyPI Pacakge or etc could be the cause of the issue.
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
    if env.state == 'ERROR':
      report.add_failed(env)
    else:
      report.add_ok(env)
