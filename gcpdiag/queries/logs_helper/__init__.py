""" Simple decorator injecting real logs.query into PureLogsQuery """

from gcpdiag.queries import logs

from .logs_query import LogsQuery as PureLogsQuery
from .search_exprs import AnyREFound, Equals, REFound


class LogsQuery:
  """ Simple decorator injecting real logs.query into PureLogsQuery """

  def __init__(self, *args, **kwargs):
    self._pure_logs_query = PureLogsQuery(logs_query_fn=logs.query,
                                          *args,
                                          **kwargs)

  def mk_query(self):
    self._pure_logs_query.mk_query()

  @property
  def has_matching_entries(self):
    return self._pure_logs_query.has_matching_entries

  def get_unique(self, fn):
    return self._pure_logs_query.get_unique(fn)
