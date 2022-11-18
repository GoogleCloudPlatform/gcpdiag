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
"""LocalityLbPolicy compatible with sessionAffinity

LocalityLbPolicy field need to be MAGLEV or RING_HASH, when sessionAffinity is not NONE.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, lb


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  bs_list = lb.get_backend_services(context.project_id)
  report_list = []

  if len(bs_list) == 0:
    report.add_skipped(None, 'no backend services found')
    return

  for bs in bs_list:
    if bs.session_affinity != 'NONE':
      if bs.locality_lb_policy not in ('MAGLEV', 'RING_HASH'):
        report_list.append(bs.name)

  if len(report_list) == 0:
    report.add_ok(project)
  else:
    result = 'Session affinity might not work in the following backend services: ' + ', '.join(
        report_list)
    report.add_failed(project, result)
