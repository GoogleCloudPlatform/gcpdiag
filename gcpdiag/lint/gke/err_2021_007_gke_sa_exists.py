# Lint as: python3
"""GKE service account permissions.

Verifying if Google Kubernetes Engine service account is created and assigned
the Kubernetes Engine Service Agent role on the project.
"""
from gcpdiag import lint, models
from gcpdiag.queries import crm, gce, iam

# defining role
ROLE = 'roles/container.serviceAgent'


# creating rule to report if default SA exists
def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')
  project_ids = {i.project_id for i in instances.values()}
  for i in project_ids:
    # fetch project number
    project = crm.get_project(i)
    sa = 'service-{}@container-engine-robot.iam.gserviceaccount.com'.format(
        project.number)
    # get iam policy
    iam_policy = iam.get_project_policy(i)
    if iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      report.add_ok(project)
    else:
      report.add_failed(project,
                        reason=f'service account: {sa}\nmissing role: {ROLE}')
