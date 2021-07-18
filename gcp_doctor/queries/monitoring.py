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
"""Queries related to Monitoring / Metrics / MQL."""

import collections.abc
import datetime
import logging
import time
from typing import Any, List, Mapping

import googleapiclient.errors

from gcp_doctor import models, utils
from gcp_doctor.queries import apis


# see: https://cloud.google.com/monitoring/api/ref_v3/rest/v3/TypedValue
def _gcp_typed_values_to_python_list(
    typed_values: List[Mapping[str, Any]]) -> List[Any]:
  out_list: List[Any] = []
  for val in typed_values:
    if 'boolValue' in val:
      out_list.append(int(val['boolValue']))
    elif 'int64Value' in val:
      out_list.append(int(val['int64Value']))
    elif 'doubleValue' in val:
      out_list.append(float(val['doubleValue']))
    elif 'stringValue' in val:
      out_list.append(val['stringValue'])
    else:
      raise RuntimeError('TypedValue type not supported: %s' % (val.keys()))
  return out_list


def period_aligned_now(period_seconds: int) -> str:
  """Return a MQL date string for the current timestamp aligned to the given period.

  This will return "now - now%period" in a MQL-parseable date string and is useful
  to get stable results. See also here for an explanation:
  (internal)
  """

  now = time.time()
  now -= now % period_seconds
  return time.strftime('%Y/%m/%d-%H:%M:%S+00:00', time.gmtime(now))


class TimeSeriesCollection(collections.abc.Mapping):
  """A mapping that stores Cloud Monitoring time series data.

  Each time series is identified by a set of labels stored as
  frozenset where the elements are strings 'label:value'. E.g.:

      frozenset({'resource.cluster_name:regional',
                 'resource.container_name:dnsmasq'})

  The frozenset is used as key to store the time series data. The data
  is a dictionary with the following fields:

  - 'start_time': timestamp string (ISO format) for the earliest point
  - 'end_time': timestamp string (ISO format) for the latest point
  - 'values': point values in bi-dimensional array-like structure:
    [[val1_t0, val2_t0], [val1_t1, val2_t1], ...]. The first dimension of
    the array is time, and the second is the value columns (usually there will
    be only one). The points are sorted chronologically (most recent point is
    the latest in the list).
  """

  _data: dict

  def __init__(self):
    # In order to ease the retrieval and matching, we store
    # label:value pairs as strings in a frozenset object.
    self._data = dict()

  def __str__(self):
    return str(self._data)

  def __repr__(self):
    return repr(self._data)

  def add_api_response(self, resource_data):
    """Add results to an existing TimeSeriesCollection object.

    The monitoring API returns paginated results, so we need to be able to add
    results to an existing TimeSeriesCollection object.
    """

    if 'timeSeriesData' not in resource_data:
      return

    for ts in resource_data['timeSeriesData']:
      # No data?
      if not ts['pointData'] or not 'values' in ts['pointData'][0] or not ts[
          'pointData'][0]['values']:
        continue

      # Use frozenset of label:value pairs as key to store the data
      labels_dict = dict()
      if 'labelValues' in ts:
        for i, value in enumerate(ts['labelValues']):
          label_name = resource_data['timeSeriesDescriptor'][
              'labelDescriptors'][i]['key']
          if 'stringValue' in value:
            labels_dict[label_name] = value['stringValue']
        labels_frozenset = frozenset(
            k + ':' + labels_dict[k] for k in labels_dict)
      else:
        labels_frozenset = frozenset()

      ts_point_data = ts['pointData']
      self._data[labels_frozenset] = {
          'labels':
              labels_dict,
          'start_time':
              ts_point_data[-1]['timeInterval']['startTime'],
          'end_time':
              ts_point_data[0]['timeInterval']['endTime'],
          'values': [
              _gcp_typed_values_to_python_list(ts_point_data[i]['values'])
              for i in reversed(range(len(ts_point_data)))
          ]
      }

  def __getitem__(self, labels):
    """Returns the time series identified by labels (frozenset)."""
    return self._data[labels]

  def __iter__(self):
    return iter(self._data)

  def __len__(self):
    return len(self._data)

  def keys(self):
    return self._data.keys()

  def items(self):
    return self._data.items()

  def values(self):
    return self._data.values()


def query(context: models.Context, query_str: str) -> TimeSeriesCollection:
  """Do a monitoring query in the specified project.

  Note that the project can be either the project where the monitored resources
  are, or a workspace host project, in which case you will get results for all
  associated monitored projects.
  """

  time_series = TimeSeriesCollection()

  mon_api = apis.get_api('monitoring', 'v3')
  for project_id in context.projects:
    try:
      request = mon_api.projects().timeSeries().query(name='projects/' +
                                                      project_id,
                                                      body={'query': query_str})

      logging.info('executing monitoring query (project: %s)', project_id)
      logging.debug('query: %s', query_str)
      pages = 0
      start_time = datetime.datetime.now()
      while request:
        pages += 1
        response = request.execute()
        time_series.add_api_response(response)
        request = mon_api.projects().timeSeries().query_next(
            previous_request=request, previous_response=response)
        if request:
          logging.info('still executing monitoring query (project: %s)',
                       project_id)
      end_time = datetime.datetime.now()
      logging.debug('query run time: %s, pages: %d', end_time - start_time,
                    pages)
    except googleapiclient.errors.HttpError as err:
      gcp_err = utils.GcpApiError(err)
      # Ignore 502 because we get that when the monitoring query times out.
      if gcp_err.status in [502]:
        logging.warning('error executing monitoring query: %s',
                        str(gcp_err.message))
      else:
        raise utils.GcpApiError(err) from err
  return time_series
