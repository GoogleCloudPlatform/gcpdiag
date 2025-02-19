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
"""Queries related to Cloud Logging.

The main functionality is querying log entries, which is supposed to be used as
follows:

1. Call query() with the logs query parameters that you need. This
   returns a LogsQuery object which can be used to retrieve the logs later.

2. Call execute_queries() to execute all log query jobs. Similar
   queries will be grouped together to minimize the number of required API
   calls.
   Multiple queries will be done in parallel, while always respecting the
   Cloud Logging limit of 60 queries per 60 seconds.

3. Use the entries property on the LogsQuery object to iterate over the fetched
   logs. Note that the entries are not guaranteed to be filtered by what was
   given in the "filter_str" argument to query(), you will need to filter out
   the entries in code as well when iterating over the log entries.

Side note: this module is not called 'logging' to avoid using the same name as
the standard python library for logging.
"""

import concurrent.futures
import dataclasses
import datetime
import logging
import threading
from typing import (Any, Deque, Dict, List, Mapping, Optional, Sequence, Set,
                    Tuple, Union)

import apiclient.errors
import dateutil.parser
import ratelimit
from boltons.iterutils import get_path

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


@dataclasses.dataclass
class _LogsQueryJob:
  """A group of log queries that will be executed with a single API call."""
  project_id: str
  resource_type: str
  log_name: str
  filters: Set[str]
  future: Optional[concurrent.futures.Future] = None


class LogsQuery:
  """A log search job that was started with prefetch_logs()."""
  job: _LogsQueryJob

  def __init__(self, job):
    self.job = job

  @property
  def entries(self) -> Sequence:
    if not self.job.future:
      raise RuntimeError(
          'log query was\'t executed. did you forget to call execute_queries()?'
      )
    elif self.job.future.running():
      logging.info(
          'waiting for logs query results (project: %s, resource type: %s)',
          self.job.project_id, self.job.resource_type)
    return self.job.future.result()


jobs_todo: Dict[Tuple[str, str, str], _LogsQueryJob] = {}


class LogEntryShort:
  """A common log entry"""
  _text: str
  _timestamp: Optional[datetime.datetime]

  def __init__(self, raw_entry):
    if isinstance(raw_entry, dict):
      self._text = get_path(raw_entry, ('textPayload',), default='')
      self._timestamp = log_entry_timestamp(raw_entry)

    if isinstance(raw_entry, str):
      self._text = raw_entry
      # we could extract timestamp from serial entries
      # but they are not always present
      # and may be unreliable as we don't know the system clock setting
      self._timestamp = None

  @property
  def text(self):
    return self._text

  @property
  def timestamp(self):
    return self._timestamp

  @property
  def timestamp_iso(self):
    if self._timestamp:
      return self._timestamp.astimezone().isoformat(sep=' ', timespec='seconds')
    return None


class LogExclusion(models.Resource):
  """A log exclusion entry"""
  _resource_data: dict
  project_id: str

  def __init__(self, project_id: str, resource_data: dict):
    super().__init__(project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def filter(self) -> str:
    return self._resource_data['filter']

  @property
  def disabled(self) -> bool:
    if 'disabled' in self._resource_data:
      return self._resource_data['disabled']
    return False


def query(project_id: str, resource_type: str, log_name: str,
          filter_str: str) -> LogsQuery:
  # Aggregate by project_id, resource_type, log_name
  job_key = (project_id, resource_type, log_name)
  job = jobs_todo.setdefault(
      job_key,
      _LogsQueryJob(
          project_id=project_id,
          resource_type=resource_type,
          log_name=log_name,
          filters=set(),
      ))
  job.filters.add(filter_str)
  return LogsQuery(job=job)


@ratelimit.sleep_and_retry
@ratelimit.limits(calls=config.get('logging_ratelimit_requests'),
                  period=config.get('logging_ratelimit_period_seconds'))
def _ratelimited_execute(req):
  """Wrapper to req.execute() with rate limiting to avoid hitting quotas."""
  try:
    return req.execute(num_retries=config.API_RETRIES)
  except apiclient.errors.HttpError as err:
    logging.error('failed to execute logging request for request %s. Error: %s',
                  req, err)
    raise utils.GcpApiError(err) from err


def _execute_query_job(job: _LogsQueryJob):
  thread = threading.current_thread()
  thread.name = f'log_query:{job.log_name}'
  logging_api = apis.get_api('logging', 'v2', job.project_id)

  # Convert "within" relative time to an absolute timestamp.
  start_time = datetime.datetime.now(
      datetime.timezone.utc) - datetime.timedelta(
          days=config.get('within_days'))
  filter_lines = ['timestamp>"%s"' % start_time.isoformat(timespec='seconds')]
  filter_lines.append('resource.type="%s"' % job.resource_type)
  if job.log_name.startswith('log_id('):
    # Special case: log_id(logname)
    # https://cloud.google.com/logging/docs/view/logging-query-language#functions
    filter_lines.append(job.log_name)
  else:
    filter_lines.append('logName="%s"' % job.log_name)
  if len(job.filters) == 1:
    filter_lines.append('(' + next(iter(job.filters)) + ')')
  else:
    filter_lines.append(
        '(' + ' OR '.join(['(' + val + ')' for val in sorted(job.filters)]) +
        ')')
  filter_str = '\n'.join(filter_lines)
  logging.info('searching logs in project %s (resource type: %s)',
               job.project_id, job.resource_type)
  # Fetch all logs and put the results in temporary storage (diskcache.Deque)
  deque = caching.get_tmp_deque('tmp-logs-')
  req = logging_api.entries().list(
      body={
          'resourceNames': [f'projects/{job.project_id}'],
          'filter': filter_str,
          'orderBy': 'timestamp desc',
          'pageSize': config.get('logging_page_size')
      })
  fetched_entries_count = 0
  query_pages = 0
  query_start_time = datetime.datetime.now()
  while req is not None:
    query_pages += 1
    res = _ratelimited_execute(req)
    if 'entries' in res:
      for e in res['entries']:
        fetched_entries_count += 1
        deque.appendleft(e)

    # Verify that we aren't above limits, exit otherwise.
    if fetched_entries_count > config.get('logging_fetch_max_entries'):
      logging.warning(
          'maximum number of log entries (%d) reached (project: %s, query: %s).',
          config.get('logging_fetch_max_entries'), job.project_id,
          filter_str.replace('\n', ' AND '))
      return deque
    run_time = (datetime.datetime.now() - query_start_time).total_seconds()
    if run_time >= config.get('logging_fetch_max_time_seconds'):
      logging.warning(
          'maximum query runtime for log query reached (project: %s, query: %s).',
          job.project_id, filter_str.replace('\n', ' AND '))
      return deque
    req = logging_api.entries().list_next(req, res)
    if req is not None:
      logging.info(
          'still fetching logs (project: %s, resource type: %s, max wait: %ds)',
          job.project_id, job.resource_type,
          config.get('logging_fetch_max_time_seconds') - run_time)

  query_end_time = datetime.datetime.now()
  logging.debug('logging query run time: %s, pages: %d, query: %s',
                query_end_time - query_start_time, query_pages,
                filter_str.replace('\n', ' AND '))

  return deque


@caching.cached_api_call
def realtime_query(project_id,
                   filter_str,
                   start_time,
                   end_time,
                   disable_paging=False):
  """Intended for use in only runbooks. use logs.query() for lint rules."""
  logging_api = apis.get_api('logging', 'v2', project_id)

  filter_lines = [filter_str]
  filter_lines.append('timestamp>"%s"' %
                      start_time.isoformat(timespec='seconds'))
  filter_lines.append('timestamp<"%s"' % end_time.isoformat(timespec='seconds'))
  filter_str = '\n'.join(filter_lines)
  logging.info('searching logs in project %s for logs between %s and %s',
               project_id, str(start_time), str(end_time))
  deque = Deque()
  req = logging_api.entries().list(
      body={
          'resourceNames': [f'projects/{project_id}'],
          'filter': filter_str,
          'orderBy': 'timestamp desc',
          'pageSize': config.get('logging_page_size')
      })
  fetched_entries_count = 0
  query_pages = 0
  query_start_time = datetime.datetime.now()
  while req is not None:
    query_pages += 1
    res = _ratelimited_execute(req)
    if 'entries' in res:
      for e in res['entries']:
        fetched_entries_count += 1
        deque.appendleft(e)

    # Verify that we aren't above limits, exit otherwise.
    if fetched_entries_count > config.get('logging_fetch_max_entries'):
      logging.warning(
          'maximum number of log entries (%d) reached (project: %s, query: %s).',
          config.get('logging_fetch_max_entries'), project_id,
          filter_str.replace('\n', ' AND '))
      return deque
    run_time = (datetime.datetime.now() - query_start_time).total_seconds()
    if run_time >= config.get('logging_fetch_max_time_seconds'):
      logging.warning(
          'maximum query runtime for log query reached (project: %s, query: %s).',
          project_id, filter_str.replace('\n', ' AND '))
      return deque
    if disable_paging:
      break
    req = logging_api.entries().list_next(req, res)
    if req is not None:
      logging.info('still fetching logs (project: %s, max wait: %ds)',
                   project_id,
                   config.get('logging_fetch_max_time_seconds') - run_time)

  query_end_time = datetime.datetime.now()
  logging.debug('logging query run time: %s, pages: %d, query: %s',
                query_end_time - query_start_time, query_pages,
                filter_str.replace('\n', ' AND '))

  return deque


def execute_queries(executor: concurrent.futures.Executor):
  global jobs_todo
  jobs_executing = jobs_todo
  jobs_todo = {}
  for job in jobs_executing.values():
    job.future = executor.submit(_execute_query_job, job)


def log_entry_timestamp(log_entry: Mapping[str, Any]) -> datetime.datetime:
  # Use receiveTimestamp so that we don't have any time synchronization issues
  # (i.e. don't trust the timestamp field)
  timestamp = log_entry.get('receiveTimestamp', None)
  if timestamp:
    return dateutil.parser.parse(timestamp)
  return timestamp


def format_log_entry(log_entry: dict) -> str:
  """Format a log_entry, as returned by LogsQuery.entries to a simple one-line
  string with the date and message."""
  log_message = None
  if 'jsonPayload' in log_entry:
    for key in ['message', 'MESSAGE']:
      if key in log_entry['jsonPayload']:
        log_message = log_entry['jsonPayload'][key]
        break
  if log_message is None:
    log_message = log_entry.get('textPayload')
  log_date = log_entry_timestamp(log_entry)
  log_date_str = log_date.astimezone().isoformat(sep=' ', timespec='seconds')
  return f'{log_date_str}: {log_message}'


def exclusions(project_id: str) -> Union[List[LogExclusion], None]:
  logging_api = apis.get_api('logging', 'v2', project_id)
  if not apis.is_enabled(project_id, 'logging'):
    return None

  log_exclusions: List[LogExclusion] = []

  fetched_entries_count = 0
  req = logging_api.exclusions().list(parent=f'projects/{project_id}')
  while req is not None:
    res = req.execute(num_retries=config.API_RETRIES)
    fetched_entries_count += 1
    if res:
      for log_exclusion_resp in res['exclusions']:
        log_exclusions.append(LogExclusion(project_id, log_exclusion_resp))
    req = logging_api.exclusions().list_next(req, res)
    if req is not None:
      # pylint: disable=logging-fstring-interpolation
      logging.info(f'still fetching log exclusions for project {project_id}')
      # pylint: enable=logging-fstring-interpolation
  return log_exclusions
