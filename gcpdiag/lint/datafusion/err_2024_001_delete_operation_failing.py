# Copyright 2024 Google LLC
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
"""Datafusion delete operation not failing.

During the instance deletion process there are cases wherein a networking
resource (i.e route) in the tenant project might not get deleted due to which
the process gets stalled in Deleting, and other reasons include missing IAM
roles in Google managed datafusion serviceAccount.
"""
import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, iam, logs

SERVICE_NAME = 'datafusion.googleapis.com'
METHOD_NAME = 'google.cloud.datafusion.v1.DataFusion.DeleteInstance'

logs_by_project = {}
projects_instances = {}
projects = {}
IAM_ROLE = 'roles/datafusion.serviceAgent'
FILTER_1 = [
    'severity=ERROR',
    f'protoPayload.serviceName:("{SERVICE_NAME}")',
    f'protoPayload.methodName:("{METHOD_NAME}")',
]


def find_instance(arr_of_datafusion_envs: dict, search_str: str):
  for instance in arr_of_datafusion_envs.values():
    if instance.full_path == search_str:
      return instance


def prefetch_rule(context: models.Context):
  projects[context.project_id] = crm.get_project(context.project_id)
  projects_instances[context.project_id] = datafusion.get_instances(context)


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='audited_resource',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=' AND '.join(FILTER_1),
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks if Data Fusion instance delete operation is failing.

  Args:
    context: The context for the rule, including the project_id, credentials,
      and other info.
    report: The report to which to report results.
  """
  if not apis.is_enabled(context.project_id, 'datafusion'):
    report.add_skipped(
        None,
        'Cloud Data Fusion API is not enabled in'
        f' { projects[context.project_id]}',
    )
    return

  datafusion_instances = projects_instances[context.project_id]
  project = projects[context.project_id]

  if not datafusion_instances:
    report.add_skipped(None,
                       f'Cloud Data Fusion instances were not found {context}')
    return

  instance_full_path_set = set()
  deleting_instance_flag = False

  for datafusion_instance in sorted(datafusion_instances.values()):
    instance_full_path_set.add(datafusion_instance.full_path)
    if datafusion_instance.is_deleting:
      deleting_instance_flag = True

  if (logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries) or deleting_instance_flag:

    iam_policy = iam.get_project_policy(context.project_id)
    datafusion_sa = (
        f'serviceAccount:service-{project.number}@gcp-sa-datafusion.iam.gserviceaccount.com'
    )
    project_iam_policy_result = iam_policy.has_role_permissions(
        datafusion_sa, IAM_ROLE)
    if not project_iam_policy_result:
      report.add_failed(project, f'{datafusion_sa}\nLacks {IAM_ROLE}')
      return

  project_ok_flag = True

  for log_entry in logs_by_project[context.project_id].entries:
    if (log_entry['protoPayload']['methodName'] == METHOD_NAME and
        log_entry['severity'] == 'ERROR' and
        log_entry['protoPayload']['resourceName'] in instance_full_path_set):

      message = log_entry['protoPayload']['status']['message']
      match = re.search(r'::(.*?):([^:]+)\.', message)
      instance_name = find_instance(datafusion_instances,
                                    log_entry['protoPayload']['resourceName'])
      if match:
        message = match.group(2)
      report.add_failed(instance_name, f'{message}')
      project_ok_flag = False
      instance_full_path_set.remove(log_entry['protoPayload']['resourceName'])

  if project_ok_flag:
    report.add_ok(project)
