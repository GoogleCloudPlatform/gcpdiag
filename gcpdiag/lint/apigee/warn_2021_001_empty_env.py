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
"""Every environment group contains at least one environment.

An environment must be a member of at least one environment group
before you can access resources defined within it.
In other words, you must assign an environment to a group before
you can use it. Or you would receive 404 errors while accessing
every hostname in the environment group.
"""
from gcpdiag import lint, models
from gcpdiag.queries import apigee


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return
  envgroup_list = apigee.get_envgroups(apigee_org)
  for envgroup in sorted(envgroup_list.values(),
                         key=lambda envgroup: envgroup.name):
    environments = apigee.get_envgroups_attachments(envgroup.full_path)
    if environments:
      report.add_ok(envgroup)
    else:
      report.add_failed(
          envgroup,
          f'No environment is attached to the environment group: {envgroup.name}\nAll of the '
          f'requests to the hostname list below will receive 404 errors: \n{envgroup.host_names}'
      )
