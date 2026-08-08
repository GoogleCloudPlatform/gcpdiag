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
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup, Tag


def extract_cell_text(element: Any) -> Optional[str]:
  """Recursively extract text from a table cell element."""
  if isinstance(element, str):
    return element
  if isinstance(element, Tag):
    return extract_cell_text(element.next)
  return None


def fetch_and_extract_table_data(
  page_url: str, tag: str = None, tag_id: str = None, class_name: str = None
) -> List[List[str]]:
  """Fetch table from URL and return row data as list of lists of cell text strings."""
  table = fetch_and_extract_table(page_url, tag=tag, tag_id=tag_id, class_name=class_name)
  if not table:
    return []
  rows_data = []
  tbody = table.find('tbody')
  rows = tbody.find_all('tr') if tbody else table.find_all('tr')
  for row in rows:
    cols = row.find_all('td')
    if not cols:
      continue
    row_cells = []
    for col in cols:
      val = extract_cell_text(col.next) or ''
      row_cells.append(val.strip())
    rows_data.append(row_cells)
  return rows_data


def fetch_and_extract_table(
  page_url: str, tag: str = None, tag_id: str = None, class_name: str = None
):
  """Fetch the table from the given page url and return it."""
  table = None
  response = get(url=page_url, timeout=10)
  response.raise_for_status()  # Raise an exception if the response is not successful
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


def fetch_all_tables(page_url: str) -> list:
  """Fetch all tables from the given page url."""
  response = get(url=page_url, timeout=10)
  response.raise_for_status()
  soup = BeautifulSoup(response.content, 'html.parser')
  return soup.find_all('table')


def get(
  url,
  params=None,
  timeout=10,
  *,
  data=None,
  headers=None,
) -> requests.Response:
  """A wrapper around requests.get for http calls which can't use the google discovery api"""
  return requests.get(url=url, params=params, timeout=timeout, data=data, headers=headers)


def parse_table(table) -> list:
  """Parse a BeautifulSoup table into a list of rows, where each row is a list of cell texts."""
  tbody = table.find('tbody')
  rows = tbody.find_all('tr') if tbody else table.find_all('tr')
  parsed_rows = []
  for row in rows:
    cols = row.find_all(['td', 'th'])
    parsed_rows.append([col.text.strip() for col in cols])
  return parsed_rows


def fetch_and_parse_all_tables(page_url: str) -> list:
  """Fetch all tables from the given page url and parse them."""
  tables = fetch_all_tables(page_url)
  return [parse_table(t) for t in tables]
