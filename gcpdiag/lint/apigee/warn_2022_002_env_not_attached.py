# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Environments are attached to Apigee X instances

Verify that environments are attached to Apigee X instances.
"""

from typing import Set

from gcpdiag import lint, models
from gcpdiag.queries import apigee


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  all_envs_list = apigee_org.environments
  if not all_envs_list:
    report.add_skipped(None, 'no Apigee environments found')
    return

  all_attached_envs_list: Set[str] = set()
  instances_list = apigee.get_instances(apigee_org)
  for instance in sorted(instances_list.values(),
                         key=lambda instance: instance.name):
    instance_envs = set(apigee.get_instances_attachments(instance.full_path))
    if instance_envs:
      all_attached_envs_list = all_attached_envs_list.union(instance_envs)

  for env in all_envs_list:
    if env.name not in all_attached_envs_list:
      report.add_failed(
          env,
          f'Environment: {env.name} is not being attached to any Apigee X instance \n'
          f'All API proxy deployment will fail in this environment')
    else:
      report.add_ok(env)
