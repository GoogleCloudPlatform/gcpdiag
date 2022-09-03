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
# Lint as: python3
"""Environment groups are created in the Apigee runtime plane.

Verify that environment groups are created in the runtime plane.
If not, we should make sure every environment group is included
in all override files where the environment is used.
"""
import re
from typing import Dict

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apigee, apis, crm, logs

MATCH_STR = 'INTERNAL: NOT_FOUND: failed to create ApigeeRoute'

k8s_container_logs_by_project = {}

APIGEE_WATCHER_FILTER = [
    'severity=ERROR', 'resource.labels.container_name= "apigee-watcher"',
    f'jsonPayload.error: "{MATCH_STR}"'
]


def prepare_rule(context: models.Context):
  k8s_container_logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_container',
      log_name='log_id("stdout")',
      filter_str=' AND '.join(APIGEE_WATCHER_FILTER))


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Apigee Connect is enabled by default for any Kubernetes cluster running Apigee service.
  if not apis.is_enabled(context.project_id, 'apigeeconnect'):
    report.add_skipped(None, 'Apigee connect api is disabled')
    return

  project = crm.get_project(context.project_id)
  env_group_errors: Dict[str, Dict[str, str]] = {}
  # Process apigee_watcher container logs and search for env group creation errors
  if k8s_container_logs_by_project.get(context.project_id) and \
    k8s_container_logs_by_project[context.project_id].entries:
    for log_entry in k8s_container_logs_by_project[context.project_id].entries:
      # Determine the problematic environment group name
      m = re.findall(
          r'cannot find ApigeeRouteConfig for environment group "([^"]*)":',
          get_path(log_entry, ('jsonPayload', 'error'), default=''))
      if not m:
        continue
      for env_group_name in m:
        cluster_name = get_path(log_entry,
                                ('resource', 'labels', 'cluster_name'),
                                default='Unknown')
        location = get_path(log_entry, ('resource', 'labels', 'location'),
                            default='Unknown')
        organization = get_path(log_entry, ('labels', 'k8s-pod/org'),
                                default='Unknown')
        if organization not in env_group_errors:
          env_group_errors[organization] = {}
        if env_group_name not in env_group_errors[organization].keys():
          env_group_errors[organization][env_group_name] = (
              f'Environment group {env_group_name} in '
              f'organization {organization}: is not created in cluster: '
              f'{cluster_name}, location: {location}')

    for org_name, env_group_error in env_group_errors.items():
      apigee_org = apigee.ApigeeOrganization(project_id=context.project_id,
                                             org_name=org_name)
      if env_group_error:
        report.add_failed(apigee_org, 'Environment group creation issue detected: \n. '+\
                          '\n. '.join(err for _, err in env_group_error.items()))
  else:
    report.add_ok(project)
