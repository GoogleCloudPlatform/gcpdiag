""" Unit tests for LogsQuery """
from unittest import TestCase

from boltons.iterutils import get_path

from .logs_query import LogsQuery
from .search_exprs import Equals


class FakeLogsResult:

  def __init__(self, entries):
    self.entries = entries


class FakeLogsQueryFn:
  """ Testing double for gcpdiag.queries.logs.query """

  def __init__(self, entries):
    self._entries = entries

  def __call__(self, project_id, resource_type, log_name, filter_str):
    key = (project_id, resource_type, log_name, filter_str)
    print(key)
    if key not in self._entries:
      raise RuntimeError(f'Unexpected call {key}')
    return self._entries[key]


ENTRIES1 = [
    {
        'one': {
            'two': 'five'
        }
    },
    {
        'one': {
            'two': 'three'
        }
    },
    {
        'one': {
            'two': 'six'
        }
    },
    {
        'one': {
            'three': 'three'
        }
    },
]

ENTRIES2 = [
    {
        'one': {
            'two': 'five',
            'data': 'alpha'
        }
    },
    {
        'one': {
            'two': 'eight',
            'data': 'beta'
        }
    },
    {
        'one': {
            'two': 'eight',
            'data': 'gamma'
        }
    },
    {
        'one': {
            'two': 'six'
        }
    },
    {
        'one': {
            'two': 'eight'
        }
    },
    {
        'one': {
            'two': 'eight',
            'data': 'gamma'
        }
    },
]


class TestLogsQuery(TestCase):
  """ Unit tests for LogsQuery """

  def setUp(self):
    self._logs_query_fn = FakeLogsQueryFn(
        entries={
            ('mytestproject', 'mytestresource', 'mytestlogname', 'one.two="three"'):
                FakeLogsResult(ENTRIES1),
            ('mytestproject', 'mytestresource', 'mytestlogname', 'one.two="seven"'):
                FakeLogsResult(ENTRIES1),
            ('mytestproject', 'mytestresource', 'mytestlogname', 'one.two="eight"'):
                FakeLogsResult(ENTRIES2),
            ('emptylogs', 'mytestresource', 'mytestlogname', 'one.two="three"'):
                FakeLogsResult([]),
            ('noresult', 'mytestresource', 'mytestlogname', 'one.two="three"'):
                FakeLogsResult([]),
        })

  def _create_query(self, search_exprs, project_id=None):
    return LogsQuery(project_id=project_id or 'mytestproject',
                     resource_type='mytestresource',
                     log_name='mytestlogname',
                     search_exprs=search_exprs,
                     logs_query_fn=self._logs_query_fn)

  def test_no_result(self):
    query = self._create_query([Equals(field='one.two', value='three')],
                               project_id='noresult')
    query.mk_query()
    self.assertFalse(query.has_matching_entries)

  def test_empty_entries(self):
    query = self._create_query([Equals(field='one.two', value='three')],
                               project_id='emptylogs')
    query.mk_query()
    self.assertFalse(query.has_matching_entries)

  def test_found(self):
    query = self._create_query([Equals(field='one.two', value='three')])
    query.mk_query()
    self.assertTrue(query.has_matching_entries)

  def test_not_found(self):
    query = self._create_query([Equals(field='one.two', value='seven')])
    query.mk_query()
    self.assertFalse(query.has_matching_entries)

  def test_unique(self):
    query = self._create_query([Equals(field='one.two', value='eight')])
    query.mk_query()
    unique = query.get_unique(
        lambda e: get_path(e, ('one', 'data'), default='unknown'))
    self.assertSetEqual(unique, {'unknown', 'beta', 'gamma'})

  def test_unique_found(self):
    query = self._create_query([Equals(field='one.two', value='eight')])
    query.mk_query()
    unique = query.get_unique(
        lambda e: get_path(e, ('one', 'data'), default='unknown'))
    self.assertSetEqual(unique, {'unknown', 'beta', 'gamma'})
