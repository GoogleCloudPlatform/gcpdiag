#
# Copyright 2021 Google LLC
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
# Lint as: python3
"""Region has sufficent resources for user to create a cluster

Region is experiencing a resource stockout while creating the cluster. \n Kindly
try creating the cluster in another zone or region. \n If the specifed
Region/Zone is a must, please reach out to GCP support team with the \n previous
details provided.
"""
import re

from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataproc, logs

# For pattern matching regex in logs
err_messages = [
    'ZONE_RESOURCE_POOL_EXHAUSTED',
    'does not have enough resources available to fulfill the request',
    'resource pool exhausted',
    'does not exist in zone',
]

logs_by_project = {}
log_search_pattern = re.compile('|'.join(err_messages))
logging_filter = '"' + '" OR "'.join(err_messages) + '"'


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='cloud_dataproc_cluster',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=logging_filter,
  )


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule is logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return
  clusters = dataproc.get_clusters(context)
  if not clusters:
    report.add_skipped(project, 'no clusters found')
    return
  if logs_by_project.get(context.project_id):
    entries = logs_by_project[context.project_id].entries
    stockout = False
    for log_entry in entries:
      msg = get_path(log_entry, ('protoPayload', 'status', 'message'),
                     default='')

      is_pattern_found = log_search_pattern.search(msg)

      # Filter out non-relevant log entries.
      if not (log_entry['severity'] == 'ERROR' and is_pattern_found):
        continue
      stockout = True
      cluster_name = get_path(
          log_entry,
          ('resource', 'labels', 'cluster_name'),
          default='Unknown Cluster',
      )
      uuid = get_path(log_entry, ('resource', 'labels', 'cluster_uuid'),
                      default='')
      region = get_path(log_entry, ('resource', 'labels', 'region'), default='')
      insert_id = get_path(log_entry, 'insertId', default='')
      message = (
          'The cluster "{}" with UUID "{}" failed \n while getting created due'
          ' to not having enough resources in designated region "{}" \n '
          ' Kindly check cloud logging insertId "{}" for more details')

      report.add_failed(project,
                        message.format(cluster_name, uuid, region, insert_id))

    # There wasn't a stockout messages in logs, project should
    # only be ok if there isn't any stockout detected
    if not stockout:
      report.add_ok(project)
