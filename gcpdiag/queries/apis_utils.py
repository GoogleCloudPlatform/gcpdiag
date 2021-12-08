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

from typing import Any, Callable, Iterator

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
