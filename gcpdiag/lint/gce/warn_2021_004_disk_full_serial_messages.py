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
"""Serial logs don't contain disk full messages

The messages:
"No space left on device" / "I/O error" / "No usable temporary directory found"
in serial output usually indicate that the disk is full.
"""

from typing import Iterable, Optional

from gcpdiag import lint, models
from gcpdiag.queries import gce, logs


class SerialOutputSearch:
  """ Search any of strings in instance's serial output """

  search_strings: Iterable[str]
  query: Optional[logs.LogsQuery]
  unique_ids: Optional[Iterable[str]]

  def __init__(self, search_strings: Iterable[str]):
    self.search_strings = search_strings
    self.query = None
    self.unique_ids = None

  def prepare(self, context: models.Context) -> None:
    self.query = logs.query(
        project_id=context.project_id,
        resource_type='gce_instance',
        log_name='log_id("serialconsole.googleapis.com/serial_port_1_output")',
        filter_str=self.mk_filters())

  def mk_filters(self) -> str:
    return ' OR '.join([self.mk_filter(s) for s in self.search_strings])

  def mk_filter(self, s: str) -> str:
    return f'textPayload=~".*{s}.*"'

  def has_results_for(self, instance_id: str) -> bool:
    return instance_id in [
        self.extract_instance_id_or_none(e) for e in self.get_query().entries
    ]

  def extract_instance_id_or_none(self, entry) -> Optional[str]:
    try:
      return entry['resource']['labels']['instance_id']
    except KeyError:
      return None

  def get_query(self) -> logs.LogsQuery:
    if self.query is None:
      raise RuntimeError('Search is not prepared yet')
    return self.query


search_by_project = {}


def prepare_rule(context: models.Context):
  s = SerialOutputSearch(search_strings=[
      'No space left on device', 'I/O error',
      'No usable temporary directory found'
  ])
  s.prepare(context)
  search_by_project[context.project_id] = s


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  search = search_by_project[context.project_id]

  instances = gce.get_instances(context).values()
  if len(instances) == 0:
    report.add_skipped(None, 'No instances found')
  else:
    for instance in instances:
      if search.has_results_for(instance_id=instance.id):
        report.add_failed(instance,
                          ('There are messages indicating that the disk might'
                           ' be full in serial output of {} ').format(
                               instance.name))
      else:
        report.add_ok(instance)
