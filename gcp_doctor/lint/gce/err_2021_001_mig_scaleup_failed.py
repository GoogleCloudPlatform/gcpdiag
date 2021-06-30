# Lint as: python3
"""Managed instance groups are not reporting scaleup failures.

Suggested Cloud Logging query:
resource.type="gce_instance" AND log_id(cloudaudit.googleapis.com/activity) AND
severity=ERROR AND protoPayload.methodName="v1.compute.instances.insert" AND
protoPayload.requestMetadata.callerSuppliedUserAgent="GCE Managed Instance Group"
"""

import operator
import re
from typing import List

from gcp_doctor import lint, models, utils
from gcp_doctor.queries import gce, logs

logs_by_project = dict()


def prepare_rule(context: models.Context):
  global logs_by_project
  migs = [
      m for m in gce.get_managed_instance_groups(context).values()
      if not m.is_gke()
  ]
  for project_id in {m.project_id for m in migs}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='gce_instance',
        log_name='log_id("cloudaudit.googleapis.com/activity")',
        filter_str='severity=ERROR AND '
        'protoPayload.methodName="v1.compute.instances.insert"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  global logs_by_project

  # Any work to do?
  # Note: we exclude GKE MIGs because we have a separate lint rule for this
  # (gke/ERR/2021_006)
  migs: List[gce.ManagedInstanceGroup] = [
      mi for mi in gce.get_managed_instance_groups(context).values()
      if not mi.is_gke()
  ]
  if not migs:
    report.add_skipped(None, 'no non-GKE managed instance groups found')

  # Process gce_instance logs and search for insert errors
  errors_by_mig = dict()
  for query in logs_by_project.values():
    for log_entry in query.entries:
      try:
        # Filter out non-relevant log entries.
        if log_entry['severity']!='ERROR' or \
          log_entry['protoPayload']['methodName']!='v1.compute.instances.insert' or \
          log_entry['protoPayload']['requestMetadata']['callerSuppliedUserAgent']!= \
          'GCE Managed Instance Group':
          continue

        # Determine to what mig this instance belongs.
        m = re.search(r'/instances/([^/]+)$',
                      log_entry['protoPayload']['resourceName'])
        if not m:
          continue
        instance_name = m.group(1)
        region = utils.zone_region(log_entry['resource']['labels']['zone'])
        ## pylint: disable=cell-var-from-loop
        mig_list = list(
            filter(
                lambda x: x.is_instance_member(
                    log_entry['resource']['labels']['project_id'], region,
                    instance_name), migs))
        if not mig_list:
          continue
        if log_entry['protoPayload']['status']['message'] == 'LIMIT_EXCEEDED':
          errors_by_mig[mig_list[0]] = 'LIMIT_EXCEEDED, possibly IP exhaustion'
        else:
          errors_by_mig[
              mig_list[0]] = log_entry['protoPayload']['status']['message']
      except KeyError:
        continue

  # Create the report.
  for mi in sorted(migs, key=operator.attrgetter('project_id', 'name')):
    if mi in errors_by_mig:
      report.add_failed(mi, errors_by_mig[mi])
    else:
      report.add_ok(mi)
