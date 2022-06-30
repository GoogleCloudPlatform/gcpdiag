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

# Lint as: python3
"""GCP project has VM Manager enabled

Google recommends enabling VM Manager. It provides visibility on software vulnerabilities,
missing updates and enables to set configuration management policies
"""
from gcpdiag import lint, models
from gcpdiag.queries import apis, crm


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  if apis.is_enabled(context.project_id, 'osconfig'):
    report.add_ok(project)
  else:
    report.add_failed(project,
                      'it is recommended to enable VM Manager on your project')
