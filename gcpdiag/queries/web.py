# Copyright 2024 Google LLC
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
"""Fetch the html content from the given page url."""

import logging

import requests
from bs4 import BeautifulSoup


def fetch_and_extract_table(page_url: str,
                            tag: str = None,
                            tag_id: str = None,
                            class_name: str = None):
  """Fetch the table from the given page url and return it."""
  table = None
  response = get(url=page_url, timeout=10)
  response.raise_for_status(
  )  # Raise an exception if the response is not successful
  soup = BeautifulSoup(response.content, 'html.parser')
  content_fetched = None
  if tag:
    if tag_id:
      content_fetched = soup.find(tag, id=tag_id)
    elif class_name:
      content_fetched = soup.find(tag, class_=class_name)
    else:
      content_fetched = soup.find(tag)

  if not content_fetched:
    logging.error('tag/id/class not found for %s with tag %s', page_url, tag)
    return table
  if tag == 'table':
    return content_fetched
  table = content_fetched.find_next('table')
  if not table:
    logging.error('Table not found for %s with tag %s', page_url, tag)
    return table

  return table


def get(
    url,
    params=None,
    timeout=10,
    *,
    data=None,
    headers=None,
) -> requests.Response:
  """A wrapper around requests.get for http calls which can't use the google discovery api"""
  return requests.get(url=url,
                      params=params,
                      timeout=timeout,
                      data=data,
                      headers=headers)
