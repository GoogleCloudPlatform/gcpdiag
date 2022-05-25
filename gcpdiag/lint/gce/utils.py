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

import datetime
import re
from typing import Dict, Iterable, Optional

from boltons.iterutils import get_path

from gcpdiag import models
from gcpdiag.queries import logs


class LogEntryShort:
  """A common log entry"""
  _text: str
  _timestamp: datetime.datetime

  def __init__(self, raw_entry):
    self._timestamp = logs.log_entry_timestamp(raw_entry)
    self._text = get_path(raw_entry, ('textPayload',), default='')

  @property
  def text(self):
    return self._text

  @property
  def timestamp(self):
    return self._timestamp

  @property
  def timestamp_iso(self):
    return self._timestamp.astimezone().isoformat(sep=' ', timespec='seconds')


class SerialOutputSearch:
  """ Search any of strings in instance's serial output """

  search_strings: Iterable[str]
  query: logs.LogsQuery
  instances_with_match: Dict[str, LogEntryShort]
  search_is_done: bool

  def __init__(self, context: models.Context, search_strings: Iterable[str]):
    self.search_strings = search_strings
    self.query = logs.query(
        project_id=context.project_id,
        resource_type='gce_instance',
        log_name='log_id("serialconsole.googleapis.com/serial_port_1_output")',
        filter_str=self._mk_filter())
    self.instances_with_match = {}
    self.search_is_done = False

  def _mk_filter(self) -> str:
    combined_filter = ' OR '.join([f'"{s}"' for s in self.search_strings])
    return f'textPayload:({combined_filter})'

  def get_last_match(self, instance_id: str) -> Optional[LogEntryShort]:
    if not self.search_is_done:
      for raw_entry in self.query.entries:
        entry_id = get_path(raw_entry, ('resource', 'labels', 'instance_id'),
                            default=None)

        if not entry_id:
          continue
        entry = LogEntryShort(raw_entry)

        if any(f in entry.text for f in self.search_strings):
          self.instances_with_match[entry_id] = entry

      self.search_is_done = True

    try:
      return self.instances_with_match[instance_id]
    except KeyError:
      return None


def is_cloudsql_peer_network(url: str) -> bool:
  prefix = 'https://www.googleapis.com/compute/v1/projects'
  pattern_non_tu = f'{prefix}/speckle-umbrella.*/cloud-sql-network-.*'
  pattern_tu = f'{prefix}/.*-tp/servicenetworking'
  return re.match(pattern_non_tu, url) is not None or \
         re.match(pattern_tu, url) is not None
