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

import concurrent.futures
import logging
import random
import time
import uuid
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import googleapiclient.errors
import httplib2

from gcpdiag import config, executor, models, utils


def _execute_single_request_wrapper(
    request_id: str,
    request: Any) -> Tuple[str, Optional[Any], Optional[Exception]]:
  response, exception = execute_single_request(request)
  return (request_id, response, exception)


def execute_concurrently(
    api: Any, requests: List[Any], context: models.Context
) -> Iterator[Tuple[Optional[str], Optional[Any], Optional[Exception]]]:
  """
  Executes a list of API requests concurrently.
  Uses ThreadPoolExecutor in API server context, batch_execute_all in CLI context.
  Yields: (request_id, response, exception)
  """
  if not requests:
    return

  if context.context_provider:
    # API Server context: Use ThreadPoolExecutor
    exec_ = executor.get_executor(context)
    request_dict: Dict[str, Any] = {str(uuid.uuid4()): req for req in requests}
    futures = {
        exec_.submit(_execute_single_request_wrapper, req_id, request): req_id
        for req_id, request in request_dict.items()
    }

    for future in concurrent.futures.as_completed(futures):
      try:
        yield future.result()
      except googleapiclient.errors.HttpError as e:
        req_id = futures[future]
        yield (req_id, None, e)
  else:
    # CLI context: Use original batch_execute_all
    yield from batch_execute_all(api, requests)


def list_all(request,
             next_function: Callable,
             response_keyword='items') -> Iterator[Any]:
  """Execute GCP API `request` and subsequently call `next_function` until
  there are no more results. Assumes that it is a list method and that
  the results are under a `items` key."""

  while True:
    try:
      response = request.execute(num_retries=config.API_RETRIES)
    except googleapiclient.errors.HttpError as err:
      raise utils.GcpApiError(err) from err

    # Empty lists are omitted in GCP API responses
    if response_keyword in response:
      yield from response[response_keyword]

    request = next_function(previous_request=request,
                            previous_response=response)
    if request is None:
      break


def multi_list_all(
    requests: list,
    next_function: Callable,
) -> Iterator[Any]:
  for req in requests:
    yield from list_all(req, next_function)


def batch_list_all(api,
                   requests: list,
                   next_function: Callable,
                   log_text: str,
                   response_keyword='items'):
  """Similar to list_all but using batch API except in TPC environment."""

  if 'googleapis.com' not in requests[0].uri:
    #  the api client library does not handle batch api calls for TPC yet, so
    #  the batch is processed and collected one at a time in that case
    for req in requests:
      yield from list_all(req, next_function)
  else:
    yield from _original_batch(api, requests, next_function, log_text,
                               response_keyword)


def _original_batch(api,
                    requests: list,
                    next_function: Callable,
                    log_text: str,
                    response_keyword='items'):
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
    for (request, response, exception) in batch_execute_all(api, next_requests):
      if exception:
        logging.info('Exception requesting %s: %s', request.uri,
                     exception.message)
        raise exception

      # add request for next page if required
      req = next_function(request, response)
      if req:
        pending_requests.append(req)
      # yield items
      if response_keyword in response:
        yield from response[response_keyword]
    page += 1


# inspired by:
# https://github.com/googleapis/google-api-python-client/blob/063dc27da5371264d36d299edb0682e63874089b/googleapiclient/http.py#L79
# but without the json "reason" handling. If we get a 403, we won't retry.
def should_retry(resp_status):
  if resp_status >= 500:
    return True
  if resp_status == 429:  # too many requests
    return True
  return False


def get_nth_exponential_random_retry(n, random_pct, multiplier, random_fn=None):
  random_fn = random_fn or random.random
  return (1 - random_fn() * random_pct) * multiplier**n


def batch_execute_all(api, requests: list):
  """Execute all `requests` using the batch API and yield (request,response,exception)
  tuples."""
  # results: (request, result, exception) tuples
  results: List[Tuple[Any, Optional[Any], Optional[Exception]]] = []
  requests_todo = requests
  requests_in_flight: List = []
  retry_count = 0

  def fetch_all_cb(request_id, response, exception):
    try:
      request = requests_in_flight[int(request_id)]
    except (IndexError, ValueError, TypeError):
      logging.debug(
          'BUG: Cannot find request %r in list of pending requests, dropping request.',
          request_id)
      return

    if exception:
      if isinstance(exception, googleapiclient.errors.HttpError) and \
        should_retry(exception.status_code) and \
        retry_count < config.API_RETRIES:
        logging.debug('received HTTP error status code %d from API, retrying',
                      exception.status_code)
        requests_todo.append(request)
      else:
        results.append((request, None, utils.GcpApiError(exception)))
      return

    if not response:
      return

    results.append((request, response, None))

  while True:
    requests_in_flight = requests_todo
    requests_todo = []
    results = []

    # Do the batch API request
    try:
      batch = api.new_batch_http_request()
      for i, req in enumerate(requests_in_flight):
        batch.add(req, callback=fetch_all_cb, request_id=str(i))
      batch.execute()
    except (googleapiclient.errors.HttpError, httplib2.HttpLib2Error) as err:
      if isinstance(err, googleapiclient.errors.HttpError):
        error_msg = f'received HTTP error status code {err.status_code} from Batch API, retrying'
      else:
        error_msg = f'received exception from Batch API: {err}, retrying'
      if (not isinstance(err, googleapiclient.errors.HttpError) or \
          should_retry(err.status_code)) \
          and retry_count < config.API_RETRIES:
        logging.debug(error_msg)
        requests_todo = requests_in_flight
        results = []
      else:
        raise utils.GcpApiError(err) from err

    # Yield results
    yield from results

    # If no requests_todo, means we are done.
    if not requests_todo:
      break

    # for example: retry delay: 20% is random, progression: 1, 1.4, 2.0, 2.7, ... 28.9 (10 retries)
    sleep_time = get_nth_exponential_random_retry(
        n=retry_count,
        random_pct=config.API_RETRY_SLEEP_RANDOMNESS_PCT,
        multiplier=config.API_RETRY_SLEEP_MULTIPLIER)
    logging.debug('sleeping %.2f seconds before retry #%d', sleep_time,
                  retry_count + 1)
    time.sleep(sleep_time)
    retry_count += 1


def execute_single_request(
    request: Any) -> Tuple[Optional[Any], Optional[Exception]]:
  """Executes a single API request and returns the response and exception."""
  try:
    response = request.execute(num_retries=config.API_RETRIES)
    return response, None
  except googleapiclient.errors.HttpError as e:
    return None, e
