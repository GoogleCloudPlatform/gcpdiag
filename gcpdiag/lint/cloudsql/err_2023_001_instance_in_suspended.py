# Copyright 2023 Google LLC
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

# Lint as: python3
"""Cloud SQL instance should not be in SUSPENDED state

The SUSPENDED state indicates a billing issue with your Google Cloud account.
You can determine your billing status by filing a Billing Support Request.
After the billing issue is resolved, the instance returns to runnable status
within a few hours. Note that suspended MySQL instances are deleted after 90
days.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, cloudsql

instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = cloudsql.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'sqladmin'):
    report.add_skipped(None, 'sqladmin is disabled')
    return

  instances = instances_by_project[context.project_id]

  if not instances:
    report.add_skipped(None, 'no CloudSQL instances found')
    return

  for instance in instances:
    if instance.is_suspended_state:
      report.add_failed(instance)
    else:
      report.add_ok(instance)
