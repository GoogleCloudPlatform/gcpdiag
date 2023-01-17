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
"""Container File System API quota not exceeded

Verify that Image Streaming has not exceeded the Container File System API quota.
That might cause a CrashLoopBackOff error on your pods.
See https://cloud.google.com/kubernetes-engine/docs/how-to/image-streaming#quota_exceeded

"""

from gcpdiag import lint, models
from gcpdiag.lint.gke import util
from gcpdiag.queries import apis, gke, logs

MATCH_STR = 'Quota exceeded for quota metric'
logs_by_project = {}


def prepare_rule(context: models.Context):
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='k8s_node',
        log_name='log_id("gcfsd")',
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

  has_image_streaming = False

  # skip entire rule is gcfs is disabled in all clusters
  for _, c in sorted(clusters.items()):
    # check if any of the clusters has image streaming
    has_image_streaming = has_image_streaming or c.has_image_streaming_enabled()

  if not has_image_streaming:
    report.add_skipped(None, 'image streaming disabled')
    return

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
      report.add_failed(
          c, 'Container File System API quota exceeded detected. Nodes:\n. ' +
          '\n. '.join(bad_nodes_by_cluster[c]))
    else:
      report.add_ok(c)
