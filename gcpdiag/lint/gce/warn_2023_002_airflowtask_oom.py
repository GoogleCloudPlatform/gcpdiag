# Copyright 2023 Google LLC
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
"""Serial logs don't contain out-of-memory message due to Airflow task run

Sometimes Composer Airflow task might be using more memory and no proper logs
will be seen
in task log. In such cases we can observe out of memory messages in the k8s node
log in the following way:
"Memory cgroup out of memory: Killed process 123456 (airflow task ru)".
"""
from typing import Optional

from gcpdiag import lint, models
from gcpdiag.lint.gce import utils
from gcpdiag.queries import gce
from gcpdiag.queries.logs import LogEntryShort

OOM_MESSAGES = ['(airflow task ru)']

logs_by_project = {}


def prepare_rule(context: models.Context):
  logs_by_project[context.project_id] = utils.SerialOutputSearch(
      context, search_strings=OOM_MESSAGES)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  search = logs_by_project[context.project_id]

  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
  else:
    for instance in sorted(instances, key=lambda i: i.full_path):
      match: Optional[LogEntryShort] = search.get_last_match(
          instance_id=instance.id)
      if match:
        report.add_failed(
            instance,
            ('There are messages indicating that OS is running'
             ' out of memory for {}\n{}: "{}" due to Airflow task run').format(
                 instance.name, match.timestamp_iso, match.text),
        )
