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
"""GCE has enough resources available to fulfill requests

Resource availablity errors can occur when using GCE resource on demand and a zone
cannot accommodate your request due to resource exhaustion for the specific VM configuration

Consider trying your request in other zones, requesting again with
a different VM hardware configuration or at a later time.
For more information, see the troubleshooting documentation.
"""
from boltons.iterutils import get_path

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, logs

METHOD_NAME_MATCH = 'compute.instances.'
STOCKOUT_MESSAGE = 'ZONE_RESOURCE_POOL_EXHAUSTED'
RESOURCE_EXHAUSTED = 'resource pool exhausted'
INSUFFICIENT_RESOURCES = 'does not have enough resources available'
LOG_FILTER = f'''
protoPayload.methodName=~("compute.instances.*insert" OR "compute.instances.resume")
protoPayload.status.message=~("{STOCKOUT_MESSAGE}" OR
"{INSUFFICIENT_RESOURCES}" OR
"{RESOURCE_EXHAUSTED}")
severity=ERROR
'''

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = logs.query(
      project_id=context.project_id,
      resource_type='gce_instance',
      log_name='log_id("cloudaudit.googleapis.com/activity")',
      filter_str=LOG_FILTER)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)
  # skip entire rule if gce api is disabled
  if not apis.is_enabled(context.project_id, 'compute'):
    report.add_skipped(project, 'compute api is disabled')
    return

  # skip entire rule if logging disabled
  if not apis.is_enabled(context.project_id, 'logging'):
    report.add_skipped(project, 'logging api is disabled')
    return

  # To hold affected zones
  stockout_zones = set()
  if logs_by_project.get(context.project_id) and \
     logs_by_project[context.project_id].entries:
    for entry in logs_by_project[context.project_id].entries:

      msg = get_path(entry, ('protoPayload', 'status', 'message'), default='')
      method = get_path(entry, ('protoPayload', 'methodName'), default='')

      if (entry['severity'] == 'ERROR' and METHOD_NAME_MATCH in method) and \
         (STOCKOUT_MESSAGE in msg) or (INSUFFICIENT_RESOURCES in msg) or \
             (RESOURCE_EXHAUSTED in msg):
        zone = get_path(entry, ('resource', 'labels', 'zone'), default='')
        if zone:
          stockout_zones.add(zone)

    if stockout_zones:
      report.add_failed(project, \
          f'Resource exhaustion in zones: {stockout_zones}')
    else:
      report.add_ok(project)
