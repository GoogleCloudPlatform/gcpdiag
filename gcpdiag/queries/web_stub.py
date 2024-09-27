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

import pathlib
import re

import requests

json_dir = pathlib.Path(__file__).parents[2] / 'test-data/web/static'


def _derive_basename_from_url(url):
  url = re.sub(r'^https?://', '', url)
  formatted_url = re.sub(r'[._=/]', '-', url)
  return formatted_url


# pylint: disable=unused-argument, protected-access
def get(url, params=None, timeout=None, *, data=None, headers=None):
  json_basename = _derive_basename_from_url(url)
  try:
    filename = str(json_dir / json_basename)
    with open(filename, encoding='utf-8') as file:
      response = requests.Response()
      response._content = file.read().encode('utf-8')
      response.status_code = 200
      response.headers['Content-Type'] = 'text/html'
      return response
  except FileNotFoundError:
    response.status_code = 404
    return response
