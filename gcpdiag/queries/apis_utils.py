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
"""GCP API-related utility functions."""

import logging
import random
import time
from typing import Any, Callable, Iterator, List

import googleapiclient.errors

from gcpdiag import config, utils


def list_all(request, next_function: Callable) -> Iterator[Any]:
  """Execute GCP API `request` and subsequently call `next_function` until
  there are no more results. Assumes that it is a list method and that
  the results are under a `items` key."""

  while True:
    try:
      response = request.execute(num_retries=config.API_RETRIES)
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err
    yield from response['items']
    request = next_function(previous_request=request,
                            previous_response=response)
    if request is None:
      break


def batch_list_all(api, requests: list, next_function: Callable, log_text: str):
  """Similar to list_all but using batch API."""
  pending_requests = requests

  page = 1
  while pending_requests:
    next_requests = pending_requests
    pending_requests = []
    if page == 1:
      logging.info(log_text)
    else:
      logging.info('%s (page: %d)', log_text, page)
    for (request, response) in batch_execute_all(api, next_requests):
      # add request for next page if required
      req = next_function(request, response)
      if req:
        pending_requests.append(req)
      # yield items
      if 'items' in response:
        yield from response['items']
    page += 1


# inspired by:
# https://github.com/googleapis/google-api-python-client/blob/063dc27da5371264d36d299edb0682e63874089b/googleapiclient/http.py#L79
# but without the json "reason" handling. If we get a 403, we won't retry.
def _should_retry(resp_status):
  if resp_status >= 500:
    return True
  if resp_status == 429:  # too many requests
    return True
  return False


def batch_execute_all(api, requests: list):
  """Execute all `requests` using the batch API and yield (request,response)
  tuples."""
  # TODO(b/200675491) implement retry of batch API request itself
  results = []
  requests_todo = requests
  requests_in_flight: List = []
  error_exceptions = []

  def fetch_all_cb(request_id, response, exception):
    if exception:
      # TODO: handle exceptions better
      if isinstance(exception, googleapiclient.errors.HttpError):
        if _should_retry(exception.status_code):
          logging.debug('received HTTP error status code %d from API, retrying',
                        exception.status_code)
          requests_todo.append(requests_in_flight[int(request_id)])
        else:
          error_exceptions.append(exception)
      return
    if not response:
      return

    try:
      req_id = int(request_id)
    except ValueError:
      logging.debug(
          'BUG: Cannot convert request ID `%r` to integer, dropping request.',
          request_id)
    if req_id not in requests:
      logging.debug(
          'BUG: Cannot find request %r in list of pending requests, dropping request.',
          req_id)
    results.append((requests[int(request_id)], response))

  for retry in range(config.API_RETRIES + 1):
    requests_in_flight = requests_todo
    requests_todo = []
    results = []

    # Do the batch API request
    try:
      batch = api.new_batch_http_request()
      for i, req in enumerate(requests_in_flight):
        batch.add(req, callback=fetch_all_cb, request_id=str(i))
      batch.execute()
    except googleapiclient.errors.HttpError as err:
      # Handle exception of Batch API call
      if _should_retry(err.status_code):
        logging.debug(
            'received HTTP error status code %d from Batch API, retrying',
            err.status_code)
        requests_todo = requests_in_flight
        results = []
      else:
        raise utils.GcpApiError(err) from err

    # Yield results
    yield from results

    # Handle retries
    if requests_todo:
      # 20% is random, progression: 1, 2, 4, 8
      sleep_time = (1 - random.random() * 0.2) * 2**retry
      logging.debug('sleeping %.2f seconds before retry #%d', sleep_time,
                    retry + 1)
      time.sleep(sleep_time)
    else:
      break

  # Any exception after the retry count has been reached?
  if error_exceptions:
    # just raise the first exception that we encountered
    raise utils.GcpApiError(error_exceptions[0])
