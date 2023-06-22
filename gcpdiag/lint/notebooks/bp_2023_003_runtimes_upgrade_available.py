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
"""Vertex AI Workbench runtimes for managed notebooks are up to date

Maintaining runtimes up to date is generally beneficial thanks to new
capabilities, framework updates, package updates, and bug fixes that have been
implemented in newer versions of your environment.
"""
from gcpdiag import lint, models
from gcpdiag.queries import apis, notebooks

runtimes_by_project = {}


def prefetch_rule(context: models.Context):
  runtimes_by_project[context.project_id] = notebooks.get_runtimes(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'notebooks'):
    report.add_skipped(None, 'Notebooks API is disabled')
    return

  runtimes = runtimes_by_project[context.project_id]

  if not runtimes:
    report.add_skipped(None, 'No runtimes found')
    return

  for runtime in runtimes.values():
    if runtime.is_upgradeable:
      report.add_failed(runtime)
    else:
      report.add_ok(runtime)
