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
from typing import Dict, Optional, Sequence, Set, Tuple

import ratelimit

from gcp_doctor import cache
from gcp_doctor.queries import apis

WITHIN_DAYS = 3
LOGGING_PAGE_SIZE = 500
LOGGING_FETCH_MAX_ENTRIES = 10000
# https://cloud.google.com/logging/quotas:
LOGGING_RATELIMIT_REQUESTS = 60
LOGGING_RATELIMIT_PERIOD_SECONDS = 60


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
          'log query wasn\'t executed. did you forget to call execute_queries()?'
      )
    elif self.job.future.running():
      logging.info('waiting for logs query results')
    return self.job.future.result()


jobs_todo: Dict[Tuple[str, str, str], _LogsQueryJob] = dict()


def query(project_id: str, resource_type: str, log_name: str,
          filter_str: str) -> LogsQuery:
  global jobs_todo
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
@ratelimit.limits(calls=LOGGING_RATELIMIT_REQUESTS,
                  period=LOGGING_RATELIMIT_PERIOD_SECONDS)
def _ratelimited_execute(req):
  """Wrapper to req.execute() with rate limiting to avoid hitting quotas."""
  return req.execute()


def _execute_query_job(logging_api, job: _LogsQueryJob):
  # Convert "within" relative time to an absolute timestamp.
  start_time = datetime.datetime.now(
      datetime.timezone.utc) - datetime.timedelta(days=WITHIN_DAYS)
  filter_lines = ['timestamp > "%s"' % start_time.isoformat(timespec='seconds')]
  filter_lines.append('resource.type = "%s"' % job.resource_type)
  filter_lines.append('logName = "%s"' % job.log_name)
  if len(job.filters) == 1:
    filter_lines.append('(' + next(iter(job.filters)) + ')')
  else:
    filter_lines.append(
        '(' + ' OR '.join(['(' + val + ')' for val in sorted(job.filters)]) +
        ')')
  filter_str = '\n'.join(filter_lines)
  logging.info('searching logs in project %s (resource type: %s)',
               job.project_id, job.resource_type)
  logging.debug('logs search filter: %s', filter_str.replace('\n', ' AND '))
  # Fetch all logs and put the results in temporary storage (diskcache.Deque)
  deque = cache.get_tmp_deque('tmp-logs-')
  req = logging_api.entries().list(
      body={
          'resourceNames': [f'projects/{job.project_id}'],
          'filter': filter_str,
          'orderBy': 'timestamp desc',
          'pageSize': LOGGING_PAGE_SIZE
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
    if fetched_entries_count > LOGGING_FETCH_MAX_ENTRIES:
      logging.warning('maximum number of log entries (%d) reached.')
      return deque
    req = logging_api.entries().list_next(req, res)

  query_end_time = datetime.datetime.now()
  logging.debug('logging query run time: %s, pages: %d',
                query_end_time - query_start_time, query_pages)

  return deque


def execute_queries(executor: concurrent.futures.Executor):
  global jobs_todo
  jobs_executing = jobs_todo
  jobs_todo = {}
  logging_api = apis.get_api('logging', 'v2')
  for job in jobs_executing.values():
    job.future = executor.submit(_execute_query_job, logging_api, job)
