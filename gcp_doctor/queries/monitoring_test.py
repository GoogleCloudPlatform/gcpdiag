# Lint as: python3
"""Test code in monitoring.py."""

from unittest import mock

from gcp_doctor import models
from gcp_doctor.queries import monitoring, monitoring_stub

DUMMY_PROJECT_NAME = 'gcpd-gce1-4exv'
DUMMY_INSTANCE_NAME = 'gce1'
DUMMY_ZONE = 'europe-west4-a'


@mock.patch('gcp_doctor.queries.apis.get_api', new=monitoring_stub.get_api_stub)
class Test:

  def test_timeserie(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    ts_col = monitoring.query(context, 'mocked query (this is ignored)')
    fs = frozenset({
        f'resource.zone:{DUMMY_ZONE}',
        f'metric.instance_name:{DUMMY_INSTANCE_NAME}'
    })
    assert fs in ts_col.keys()
    value = ts_col[fs]

    # expected data:
    # {
    #   'labels': {
    #     'resource.zone': 'europe-west4-a',
    #     'metric.instance_name': 'gce1'
    #   },
    #   'start_time': '2021-05-19T15:40:31.414435Z',
    #   'end_time': '2021-05-19T15:45:31.414435Z',
    #   'values': [[10917.0, 5], [11187.0, 4]]
    # }
    assert value['labels']['metric.instance_name'] == 'gce1'
    assert 'start_time' in value
    assert 'end_time' in value
    assert isinstance(value['values'][0][0], float)
    assert isinstance(value['values'][1][0], float)
    assert isinstance(value['values'][0][1], int)
    assert isinstance(value['values'][1][1], int)
