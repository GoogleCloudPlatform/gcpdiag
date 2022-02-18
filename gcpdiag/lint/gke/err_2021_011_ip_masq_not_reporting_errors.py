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
"""ip-masq-agent not reporting errors

If ip-masq-agent is reporting errors, it is possible that the config received
is invalid. In that case, it is possible that the applied config is not
reflecting the desired masquerading behavior, which could lead to unexpected
connectivity issues.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

IP_MASQ_AGENT_CONTAINER_NAME = 'ip-masq-agent'

# k8s_container
ip_masq_container_errors = {}


def prepare_rule(context: models.Context):
  ip_masq_container_errors[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='k8s_container',
      log_name='log_id("stderr")',
      filter_str='severity=ERROR AND '+\
      f'resource.labels.container_name="{IP_MASQ_AGENT_CONTAINER_NAME}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  def filter_f(log_entry):
    try:
      container_name = log_entry['resource']['labels']['container_name']
      if (log_entry['severity'] == 'ERROR' and
          container_name == IP_MASQ_AGENT_CONTAINER_NAME):
        return True
    except KeyError:
      return False

  clusters_with_errors = util.gke_logs_find_bad_cluster(
      context=context,
      logs_by_project=ip_masq_container_errors,
      filter_f=filter_f)

  # Generate report
  for c in clusters.values():
    if c in clusters_with_errors:
      msg = clusters_with_errors[c]
      report.add_failed(c, f'Error message:\n```\n {msg}\n```')
    else:
      report.add_ok(c)
