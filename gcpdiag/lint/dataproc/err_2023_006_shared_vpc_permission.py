# Copyright 2023 Google LLC
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
"""DataProc Cluster user has networking permissions on host project.

Dataproc cluster launched on a shared VPC requires permission on the Host Subnet
that is used to create the cluster. If the required set of permissions are not
available, the cluster launch operation fails.
The permission is to be set for DataProc service agent from service project.
"""

from gcpdiag import lint, models
from gcpdiag.queries import crm, dataproc, gce, iam, network

COMPUTE_NETWORK_USER_ROLE = 'roles/compute.networkUser'
COMPUTE_NETWORK_VIEWER_ROLE = 'roles/compute.networkViewer'


def validate_iam_roles(
    context: models.Context,
    service_account: str,
    service_account_name: str,
    host_project: str,
    host_iam_policy: iam.BaseIAMPolicy,
    cluster: dataproc.Cluster,
    report: lint.LintReportRuleInterface,
    master_vm: gce.Instance,
) -> bool:
  # Project Level Check
  sa_has_net_user = host_iam_policy.has_role_permissions(
      f'serviceAccount:{service_account}', COMPUTE_NETWORK_USER_ROLE)

  # Subnet level check
  if not sa_has_net_user:
    for subnet in master_vm.subnetworks:
      if subnet.region == cluster.region:
        subnet_iam_policy = network.get_subnetwork_iam_policy(
            context, subnet.region, subnet.name)
        sa_has_net_user = subnet_iam_policy.has_role_permissions(
            f'serviceAccount:{service_account}',
            COMPUTE_NETWORK_USER_ROLE,
        )
        if sa_has_net_user:
          return True

      if not sa_has_net_user:
        report.add_failed(
            cluster,
            (f'{service_account_name} {service_account} '
             f'missing {COMPUTE_NETWORK_USER_ROLE} IAM role '
             f'in host project {host_project}'),
        )
        return False

  return True


def shared_vpc_check(host_project, service_project):
  return host_project == service_project


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  clusters = dataproc.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'No Clusters Found')

  service_project = crm.get_project(context.project_id)
  dataproc_service_agent = (f'service-{service_project.number}'
                            '@dataproc-accounts.iam.gserviceaccount.com')

  for cluster in clusters:
    if cluster.is_gce_cluster:
      cluster_network = cluster.gce_network_uri
      host_project = str(
          str(cluster_network).rsplit('/projects/',
                                      maxsplit=1)[1]).rsplit('/global/networks',
                                                             maxsplit=1)[0]

      no_shared_vpc = shared_vpc_check(host_project, context.project_id)
      if not no_shared_vpc:
        try:
          if cluster.is_ha_cluster:
            master_vm = gce.get_instance(
                project_id=context.project_id,
                zone=cluster.zone,
                instance_name=f'{cluster.name}-m-0',
            )
          else:
            master_vm = gce.get_instance(
                project_id=context.project_id,
                zone=cluster.zone,
                instance_name=f'{cluster.name}-m',
            )
        except:  # pylint: disable=bare-except
          report.add_skipped(
              cluster, 'Master VM is not running. Not able to check Network')
          continue

        host_project_context = context.copy_with(project_id=host_project)
        host_iam_policy = iam.get_project_policy(host_project_context)
        dataproc_sa_is_valid = validate_iam_roles(
            host_project_context,
            dataproc_service_agent,
            'Dataproc Service Agent service account',
            host_project,
            host_iam_policy,
            cluster,
            report,
            master_vm,
        )
        if dataproc_sa_is_valid:
          report.add_ok(cluster)
      else:
        report.add_skipped(cluster, f'Not on Shared VPC : {cluster}')
    else:
      report.add_skipped(cluster, f'Not a GCE cluster : {cluster}')
