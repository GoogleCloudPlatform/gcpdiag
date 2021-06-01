# Lint as: python3
"""GCE instance service account permissions for logging.

The service account used by GCE instance should have the logging.logWriter
permission, otherwise, if you install the logging agent, it won't be able
to send the logs to Cloud Logging.
"""

import operator as op

from gcp_doctor import lint, models
from gcp_doctor.queries import gce, iam

ROLE = 'roles/logging.logWriter'


def prefetch_rule(context: models.Context):
  # Make sure that we have the IAM policy in cache.
  project_ids = {i.project_id for i in gce.get_instances(context).values()}
  for pid in project_ids:
    iam.get_project_policy(pid)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = gce.get_instances(context)
  instances_count = 0
  for i in sorted(instances.values(), key=op.attrgetter('project_id', 'name')):
    # GKE nodes are checked by another test.
    if i.is_gke_node():
      continue
    instances_count += 1
    iam_policy = iam.get_project_policy(i.project_id)
    sa = i.service_account
    if not sa:
      report.add_failed(i, 'no service account')
    elif not iam_policy.has_role_permissions(f'serviceAccount:{sa}', ROLE):
      report.add_failed(i, f'service account: {sa}\nmissing role: {ROLE}')
    else:
      report.add_ok(i)
  if not instances_count:
    report.add_skipped(None, 'no instances found')
