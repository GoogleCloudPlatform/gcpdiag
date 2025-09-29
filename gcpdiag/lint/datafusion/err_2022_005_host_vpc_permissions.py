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

# Note that we don't have a general rule that checks this for all products,
# because the grant is done lazily, as soon as it is needed. So check that the
# grant is there only when resources of a certain product (like GKE clusters)
# are present, and we know that the grant is necessary for the correct
# operation of that product. Copy the rule for other products, as necessary.
"""
Private Data Fusion instance has networking permissions.

Private Data Fusion instance requires networking permissions.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, datafusion, iam, network

COMPUTE_NETWORK_USER_ROLE = 'roles/compute.networkUser'
COMPUTE_NETWORK_VIEWER_ROLE = 'roles/compute.networkViewer'


def validate_iam_roles(context: models.Context, service_account: str,
                       service_account_name: str, host_project: str,
                       host_iam_policy: iam.BaseIAMPolicy,
                       instance: datafusion.Instance,
                       report: lint.LintReportRuleInterface) -> bool:

  # Project Level Check
  sa_has_net_user = host_iam_policy.has_role_permissions(
      f'serviceAccount:{service_account}', COMPUTE_NETWORK_USER_ROLE)

  if not sa_has_net_user:
    sa_has_net_viewer = host_iam_policy.has_role_permissions(
        f'serviceAccount:{service_account}', COMPUTE_NETWORK_VIEWER_ROLE)

    # Subnet Level Check
    for subnet in instance.network.subnetworks.values():
      if subnet.region == instance.location:
        subnet_iam_policy = network.get_subnetwork_iam_policy(
            context, instance.location, subnet.name)

        sa_has_net_user = subnet_iam_policy.has_role_permissions(
            f'serviceAccount:{service_account}', COMPUTE_NETWORK_USER_ROLE)
        if sa_has_net_user:
          break

    if not sa_has_net_viewer and sa_has_net_user:
      report.add_failed(instance,
                        (f'{service_account_name} {service_account} '
                         f'missing {COMPUTE_NETWORK_VIEWER_ROLE} IAM role on '
                         f'host project {host_project}.'))
      return False
    elif sa_has_net_viewer and not sa_has_net_user:
      report.add_failed(instance,
                        (f'{service_account_name} {service_account} '
                         f'missing {COMPUTE_NETWORK_USER_ROLE} IAM role on '
                         f'subnetwork with region {instance.location} '
                         f'in host network {instance.network.short_path}'))
      return False
    elif not sa_has_net_viewer and not sa_has_net_user:
      report.add_failed(instance,
                        (f'{service_account_name} {service_account} '
                         f'missing {COMPUTE_NETWORK_USER_ROLE} IAM role on '
                         f'host project {host_project}.'))
      return False

  return True


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):

  instances = datafusion.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')

  service_project = crm.get_project(context.project_id)
  datafusion_service_agent = (f'service-{service_project.number}'
                              f'@gcp-sa-datafusion.iam.gserviceaccount.com')
  dataproc_service_agent = (f'service-{service_project.number}'
                            f'@dataproc-accounts.iam.gserviceaccount.com')

  for instance in instances.values():
    if instance.uses_shared_vpc and not instance.is_deleting:

      host_project = instance.network.project_id
      host_project_context = context.copy_with(project_id=host_project)
      host_iam_policy = iam.get_project_policy(host_project_context)

      datafusion_sa_is_valid = validate_iam_roles(
          host_project_context,
          datafusion_service_agent,
          'Cloud Data Fusion API Service Agent',
          host_project,
          host_iam_policy,
          instance,
          report,
      )

      dataproc_sa_is_valid = validate_iam_roles(
          host_project_context,
          dataproc_service_agent,
          'Dataproc Service Agent service account',
          host_project,
          host_iam_policy,
          instance,
          report,
      )

      if datafusion_sa_is_valid and dataproc_sa_is_valid:
        report.add_ok(instance)

    else:
      report.add_ok(instance)
