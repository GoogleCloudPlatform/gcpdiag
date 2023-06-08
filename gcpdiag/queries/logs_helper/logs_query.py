""" Helper to work with gcpdiag.queries.logs module """
from functools import cached_property


class LogsQuery:
  """
  Encapsulates gcpdiag queries to Cloud Logging

  By default gcpdiag logs module combines different logging queries
  into a single query. Therefore we might by simply inspecting the output
  of gcpdiag's logs module query we might face unrelated log entries. So
  we have to filter entries again.

  This helper class helps with accoplishing this double filtering.

  It receives a parameter search_exprs, which contains a list of classes
  (see logs_helper/logs_query.py) encapsulating search operations both
  for Cloud Logging filter and later python filter.

  Example:
    LogsQuery(
      ...
      search_exprs=[
        REFound(field='textPayload', re_exp='.*hello world.*'),
      ],
      ...
    )

    is basically the same as fetching textPayload=~'.*hello world.*' from
    Cloud Logging using logs.query and then filter, like:

    if logs_by_project.get(context.project_id) and \
       logs_by_project[context.project_id].entries:
      for log_entry in logs_by_project[context.project_id].entries:
        # Filter out non-relevant log entries.
        if re.match('.*hello world.*', log_entry['textPayload']) and ...:
          continue

        # Do something with the matching entry

  it abstracts usual questions we're asking to Cloud Logging:
    - if we have any such entries at all (has_matching_entries method)
    - extract a list of unique values from all relevant log entries
      (get_unique method)
      Example - getting unique dataflow job ids that have matching entries:

        def prepare_rule(...):
          global query
          query = LogsQuery(...)
          query.mk_query()

        def run_rule(...):
          unique_jobs = logs_query.get_unique(
            lambda e: get_path(e, ('resource', 'labels', 'job_name'), default='unknown job')
          )

      This will give us unique resource.labels.job_name values found among matching entries.


  IMPORTANT:
    gcpdiag's logs.query are supposed to be used only in prepare_rule(), so
    LogsQuery needs to be defined and run (mk_query method) there as well.

  """

  def __init__(self, project_id, resource_type, log_name, search_exprs,
               logs_query_fn):
    self._project_id = project_id
    self._resource_type = resource_type
    self._log_name = log_name
    self._search_exprs = search_exprs
    self._logs_query_fn = logs_query_fn
    self.project_id = None
    self._result = None

  def mk_query(self):
    self._result = self._logs_query_fn(project_id=self._project_id,
                                       resource_type=self._resource_type,
                                       log_name=self._log_name,
                                       filter_str=self._stackdriver_expr)

  @cached_property
  def has_matching_entries(self):
    if not self._result or not self._result.entries:
      return False
    return any(self._is_log_entry_matches(e) for e in self._result.entries)

  def get_unique(self, fn):
    if not self._result or not self._result.entries:
      return set()
    return {
        fn(e) for e in self._result.entries if self._is_log_entry_matches(e)
    }

  @property
  def _stackdriver_expr(self):
    return ' AND '.join(e.stackdriver_expr for e in self._search_exprs)

  def _is_log_entry_matches(self, log_entry):
    return all(e.is_log_entry_matches(log_entry) for e in self._search_exprs)
