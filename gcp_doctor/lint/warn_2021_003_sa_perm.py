# Lint as: python3
"""GCE Compute Engine service agent permissions.

This service account is designed specifically for Compute Engine
to perform its service duties on your project. It relies on the
Service Agent IAM Policy granted on your Google Cloud Project.
"""
from gcp_doctor import lint, models
from gcp_doctor.queries import crm, gce, iam

# defining role
ROLE = 'roles/compute.serviceAgent'


# creating rule to report if default SA exists
def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  if not instances:
    report.add_skipped(None, 'no instances found')
  project_ids = {i.project_id for i in instances.values()}
  for i in project_ids:
    # fetch project number
    project = crm.get_project(i)
    sa = 'service-{}@compute-system.iam.gserviceaccount.com'.format(
        project.number)
    # get iam policy
    iam_policy = iam.get_project_policy(i)
    if iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      report.add_ok(project)
    else:
      report.add_failed(project,
                        reason=f'service account: {sa}\nmissing role: {ROLE}')
