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

# Lint as: python3
"""Various utility functions for GCE linters."""

import re
from typing import Dict, Iterable, Optional

from boltons.iterutils import get_path

from gcpdiag import config, models
from gcpdiag.queries import apis, gce, logs


class SerialOutputSearch:
  """ Search any of strings in instance's serial output """

  search_strings: Iterable[str]
  query: logs.LogsQuery
  instances_with_match: Dict[str, logs.LogEntryShort]
  search_is_done: bool
  serial_port_outputs: gce.SerialOutputQuery

  def __init__(self,
               context: models.Context,
               search_strings: Iterable[str],
               custom_filter: str = None):
    self.search_strings = search_strings
    self.query = logs.query(
        project_id=context.project_id,
        resource_type='gce_instance',
        log_name='log_id("serialconsole.googleapis.com/serial_port_1_output")',
        filter_str=custom_filter if custom_filter else self._mk_filter())
    if config.get('enable_gce_serial_buffer'):
      self.serial_port_outputs = gce.fetch_serial_port_outputs(context)

    self.instances_with_match = {}
    self.search_is_done = False

  def _mk_filter(self) -> str:
    combined_filter = ' OR '.join([f'"{s}"' for s in self.search_strings])
    return f'textPayload:({combined_filter})'

  def get_last_match(self, instance_id: str) -> Optional[logs.LogEntryShort]:
    if not self.search_is_done:
      self.get_all_instance_with_match()
    return self.instances_with_match.get(instance_id, None)

  def get_all_instance_with_match(self):
    for raw_entry in self.query.entries:
      entry_id = get_path(raw_entry, ('resource', 'labels', 'instance_id'),
                          default=None)
      if not entry_id:
        continue
      entry = logs.LogEntryShort(raw_entry)
      if any(f in entry.text for f in self.search_strings):
        self.instances_with_match[entry_id] = entry

    # If user has enabled direct serial port log fetching
    if config.get('enable_gce_serial_buffer'):
      for output in self.serial_port_outputs.entries:
        # there is no reliable timestamps so we rely on the order the contents were delivered
        # the order of the output contents is always consistent
        # start from the buttom for the most recent entry
        for serial_entry in reversed(output.contents):
          if not self.instances_with_match.get(output.instance_id):
            if any(f in serial_entry for f in self.search_strings):
              self.instances_with_match[
                  output.instance_id] = logs.LogEntryShort(serial_entry)

    self.search_is_done = True


class QueryCloudLogs:
  """ Query Cloud Logging for strings/methods/payloads etc. """

  query: logs.LogsQuery
  instances_with_match: Dict[str, logs.LogEntryShort]

  def __init__(self,
               project_id: str,
               resource_type: str,
               filter_log: Iterable[str],
               logid: Iterable[str] = None):

    self.filter_log = ' OR '.join([f'{s}' for s in filter_log])
    self.log_id = self._mk_filter(logid)

    self.log_query = logs.query(project_id=project_id,
                                resource_type=resource_type,
                                log_name=self.log_id,
                                filter_str=self.filter_log)

  def _mk_filter(self, logid) -> str:
    combined_filter = ' OR '.join([f'"{s}"' for s in logid])
    return f'log_id({combined_filter})'

  def get_entries(self, instance_id: str) -> dict:
    self.instances_with_match = {}
    raw_entry = None
    for raw_entry in self.log_query.entries:
      entry_id = get_path(raw_entry, ('resource', 'labels', 'instance_id'),
                          default=None)
      if entry_id == instance_id:
        self.instances_with_match[instance_id] = raw_entry
    return self.instances_with_match


def is_cloudsql_peer_network(url: str) -> bool:
  prefix = 'https://www.googleapis.com/compute/v1/projects'
  pattern_non_tu = f'{prefix}/speckle-umbrella.*/cloud-sql-network-.*'
  pattern_tu = f'{prefix}/.*-tp/servicenetworking'
  return re.match(pattern_non_tu, url) is not None or \
         re.match(pattern_tu, url) is not None


def is_serial_port_one_logs_available(context: models.Context):
  return (apis.is_enabled(context.project_id, 'logging') and \
    gce.is_project_serial_port_logging_enabled(context.project_id)) or \
    gce.is_serial_port_buffer_enabled()
