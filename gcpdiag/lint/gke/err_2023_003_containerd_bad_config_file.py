# Copyright 2022 Google LLC
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
"""containerd config.toml is valid

`containerd` container runtime is a crucial component of a GKE cluster that
runs on all nodes. If its configuration file was customized and became
invalid, `containerd` can't be started and its node will stay in `NotReady`
state.
"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MAX_NODES_TO_REPORT = 10
MATCH_STR = 'containerd: failed to load TOML'
logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_node',
        log_name='log_id("container-runtime")',
        filter_str=f'jsonPayload.MESSAGE:"{MATCH_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Skip entire rule if Cloud Logging is disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(None, 'logging api is disabled')
    return

  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Search the logs.
  def filter_f(log_entry):
    try:
      return MATCH_STR in log_entry['jsonPayload']['MESSAGE']
    except KeyError:
      return False

  bad_nodes_by_cluster = util.gke_logs_find_bad_nodes(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_nodes_by_cluster:
      # Report only MAX_NODES_TO_REPORT nodes to limit the output for big clusters
      report.add_failed(
          c,
          'Invalid config.toml configuration for containerd is detected. Nodes:\n. '
          + '\n. '.join(list(bad_nodes_by_cluster[c])[:MAX_NODES_TO_REPORT]) +
          ('\n. + ' + str(len(bad_nodes_by_cluster[c]) - MAX_NODES_TO_REPORT) +
           ' more node(s)') *
          (len(bad_nodes_by_cluster[c]) > MAX_NODES_TO_REPORT))
    else:
      report.add_ok(c)
