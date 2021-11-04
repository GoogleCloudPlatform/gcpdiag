# Copyright 2021 Google LLC
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
"""Google Groups for RBAC enabled.

Enable Google Groups for RBAC so cluster administrators do not need to
manage permissions manually for each user on the cluster and so Workspace
administrators can manage user accounts, such as revoking access when
someone leaves your organization.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gke


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
  for _, c in sorted(clusters.items()):
    disabled = []
    if not c.has_authenticator_group_enabled():
      disabled.append('groups')
    if disabled:
      report.add_failed(c, ' and '.join(disabled) + ' are disabled')
    else:
      report.add_ok(c)
