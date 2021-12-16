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
from typing import Any, Callable, Iterable, Iterator

import googleapiclient

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


def batch_list_all(api, requests: Iterable, next_function: Callable,
                   log_text: str):
  """Similar to list_all but using batch API."""
  try:
    items = []
    additional_pages_to_fetch = []
    pending_requests = list(requests)

    # TODO(b/200675491) implement retry

    def fetch_all_cb(request_id, response, exception):
      if exception:
        logging.error('exception when %s: %s', log_text, exception)
        return
      if not response or 'items' not in response:
        return
      items.extend(response['items'])
      additional_pages_to_fetch.append(
          (pending_requests[int(request_id)], response))

    page = 1
    while pending_requests:
      batch = api.new_batch_http_request()
      for i, req in enumerate(pending_requests):
        batch.add(req, callback=fetch_all_cb, request_id=str(i))
      if page <= 1:
        logging.info(log_text)
      else:
        logging.info('%s (page: %d)', log_text, page)
      batch.execute()
      yield from items
      items = []

      # Do we need to fetch any additional pages?
      pending_requests = []
      for p in additional_pages_to_fetch:
        req = next_function(p[0], p[1])
        if req:
          pending_requests.append(req)
      additional_pages_to_fetch = []
      page += 1
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  yield from items
