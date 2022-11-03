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
"""Cloud KMS key is enabled and could be accessed by Apigee Service Agent

Verify that the runtime database encryption key and disk encryption key
are not disabled or destroyed and the Apigee Service Agent account has the permission
to access the KMS keys
"""

from gcpdiag import lint, models
from gcpdiag.queries import apigee, crm, kms

SA = 'service-{project_number}@gcp-sa-apigee.iam.gserviceaccount.com'
ROLE = 'roles/cloudkms.cryptoKeyEncrypterDecrypter'

RUNTIME_DATABASE_ENCRYPTION_KEY_STRING = 'runtime database encryption key'
DISK_ENCRYPTION_KEY_STRING = 'disk encryption key'


def _run_rule_kms_key(report: lint.LintReportRuleInterface, kms_key_name: str,
                      kms_key_mode: str, service_account: str):
  if kms_key_name:
    kms_key = kms.get_crypto_key(kms_key_name)
    if _is_valid_kms_key(kms_key):
      if not _apigee_sa_has_role_permissions(kms_key_name, service_account):
        report.add_failed(
            kms_key,
            (f'service account: {service_account}\n'
             f'missing role: {ROLE} for {kms_key_mode} {kms_key_name}'))
      else:
        report.add_ok(kms_key)
    else:
      report.add_failed(
          kms_key, f'Key {kms_key_name} is not valid (destroyed or disabled)')
  else:
    report.add_skipped(None, f'{kms_key_mode} is not configured')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  apigee_org = apigee.get_org(context)
  if apigee_org is None:
    report.add_skipped(None, 'no Apigee organizations found')
    return

  if apigee_org.runtime_type == 'HYBRID':
    report.add_skipped(None, 'This rule only applies to Apigee X product')
    return

  project = crm.get_project(context.project_id)
  service_account = SA.format(project_number=project.number)

  # Verify permissions on runtime database encryption key
  kms_key_name = apigee_org.runtime_database_encryption_key_name
  _run_rule_kms_key(report, kms_key_name,
                    RUNTIME_DATABASE_ENCRYPTION_KEY_STRING, service_account)

  # Verify permissions on disk encryption key
  instances_list = apigee.get_instances(apigee_org)
  for instance in sorted(instances_list.values(),
                         key=lambda instance: instance.name):
    kms_key_name = instance.disk_encryption_key_name
    _run_rule_kms_key(report, kms_key_name, DISK_ENCRYPTION_KEY_STRING,
                      service_account)


def _is_valid_kms_key(kms_key):
  return not kms_key.is_destroyed() and kms_key.is_enabled()


def _apigee_sa_has_role_permissions(kms_key_name, service_account):
  iam_policy = kms.get_crypto_key_iam_policy(kms_key_name)
  return iam_policy.has_role_permissions(f'serviceAccount:{service_account}',
                                         ROLE)
