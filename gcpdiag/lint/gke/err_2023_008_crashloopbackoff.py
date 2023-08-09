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
""" GKE Cluster does not have any pods in Crashloopbackoff state.

CrashLoopBackOff indicates that a container is repeatedly crashing after restarting.
A container might crash for many reasons, and checking a Pod's logs might aid in
troubleshooting the root cause.
"""
import logging
import re

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR = 'CrashLoopBackOff'
logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_node',
        log_name='log_id("kubelet")',
        filter_str=f'jsonPayload.MESSAGE:"{MATCH_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')
    return

  # Search the logs.
  def filter_f(log_entry):
    try:
      return MATCH_STR in log_entry['jsonPayload']['MESSAGE']
    except KeyError:
      return False

  bad_clusters = util.gke_logs_find_bad_clusters(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)

  for _, c in sorted(clusters.items()):
    if c in bad_clusters:
      pod_names = set()
      for query in logs_by_project.values():
        for log_entry in query.entries:
          try:
            log_cluster_name = log_entry['resource']['labels']['cluster_name']
            log_cluster_location = log_entry['resource']['labels']['location']
          except KeyError:
            logging.warning(
                'Skip: Failed to get cluster name/location from log entry %s',
                log_entry)
            continue

          if (log_cluster_location == c.location and
              log_cluster_name == c.name):
            pod_name = re.search(r'pod=\"(.*?\/.*?)-.*?\"',
                                 log_entry['jsonPayload']['MESSAGE'])
            if pod_name:
              pod_names.add(pod_name.group(1))
      report.add_failed(c,
                        reason='Failing pods in namespace/workload: ' +
                        ', '.join(pod_names))
    else:
      report.add_ok(c)
