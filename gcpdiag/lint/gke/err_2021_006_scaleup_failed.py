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
"""GKE Autoscaler isn't reporting scaleup failures.

If the GKE autoscaler reported a problem when trying to add nodes to a cluster,
it could mean that you don't have enough resources to accomodate for new nodes.
E.g. you might not have enough free IP addresses in the GKE cluster network.
"""

import collections
import re

from gcpdiag import lint, models
from gcpdiag.queries import gke, logs

# k8s_cluster, container.googleapis.com/cluster-autoscaler-visibility
ca_logs_by_project = dict()
# gce_instance, cloudaudit.googleapis.com/activity
gce_logs_by_project = dict()


def prepare_rule(context: models.Context):
  global ca_logs_by_project
  global gce_logs_by_project
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    ca_logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_cluster',
        log_name=
        'log_id("container.googleapis.com/cluster-autoscaler-visibility")',
        filter_str=
        'jsonPayload.resultInfo.results.errorMsg.messageId:"scale.up.error"')
    gce_logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='gce_instance',
        log_name='log_id("cloudaudit.googleapis.com/activity")',
        filter_str='severity=ERROR AND '
        'protoPayload.methodName="v1.compute.instances.insert"')
    # Note: we don't filter by callerSuppliedUserAgent because this will be
    # removed anyway because of search job aggregation.
    #AND '
    #'protoPayload.requestMetadata.callerSuppliedUserAgent="GCE Managed Instance Group for GKE"'


def is_mig_instance(mig_name: str, instance_name: str):
  """Verify that an instance is part of a mig using naming conventions."""
  if mig_name.endswith('-grp'):
    mig_prefix = mig_name[:-4]
    if instance_name.startswith(mig_prefix):
      return True
  return False


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  global ca_logs_by_project
  global gce_logs_by_project

  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Correlation dicts, so that we can determine resources based on log labels:
  try:
    cluster_by_mig = dict()
    cluster_migs = collections.defaultdict(set)
    for c in clusters.values():
      for np in c.nodepools:
        for mig in np.instance_groups:
          cluster_by_mig[mig.name] = c
          cluster_migs[c].add(mig.name)
  except KeyError:
    pass

  # Collect errors by mig name.
  mig_errors = dict()

  # Process gce_instance logs and search for VM creation errors
  for query in gce_logs_by_project.values():
    for log_entry in query.entries:
      try:
        # Filter out non-relevant log entries.
        if log_entry['severity']!='ERROR' or \
          log_entry['protoPayload']['methodName']!='v1.compute.instances.insert' or \
          log_entry['protoPayload']['requestMetadata']['callerSuppliedUserAgent']!= \
          'GCE Managed Instance Group for GKE':
          continue
        # Determine mig name.
        m = re.search(r'/instances/([^/]+)$',
                      log_entry['protoPayload']['resourceName'])
        if not m:
          continue
        instance_name = m.group(1)
        # pylint: disable=cell-var-from-loop
        mig = list(
            filter(lambda x: is_mig_instance(x, instance_name),
                   cluster_by_mig.keys()))
        if not mig:
          continue
        if log_entry['protoPayload']['status']['message'] == 'LIMIT_EXCEEDED':
          mig_errors[mig[0]] = 'LIMIT_EXCEEDED, possibly IP exhaustion'
        else:
          mig_errors[mig[0]] = log_entry['protoPayload']['status']['message']
      except KeyError:
        pass

  # Process cluster autoscaler logs
  for query in ca_logs_by_project.values():
    for log_entry in query.entries:
      try:
        for r in log_entry['jsonPayload']['resultInfo']['results']:
          if r['errorMsg']['messageId'].startswith('scale.up.error'):
            for p in r['errorMsg']['parameters']:
              m = re.search(r'/instanceGroups/([^/]+)$', p)
              if m:
                mig_errors.setdefault(m.group(1), r['errorMsg']['messageId'])
      except KeyError:
        pass

  # Create the report.
  for _, c in sorted(clusters.items()):
    cluster_mig_errors = cluster_migs.get(c,
                                          set()).intersection(mig_errors.keys())
    if cluster_mig_errors:
      report.add_failed(
          c, 'Scale up failures detected on managed instance groups:\n. '+\
              '\n. '.join(f'{mig} ({mig_errors[mig]})' for mig in cluster_mig_errors))
    else:
      report.add_ok(c)
