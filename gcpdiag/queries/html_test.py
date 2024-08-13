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

# Lint as: python3
"""Test code in html.py."""

import unittest
from unittest import mock

from gcpdiag.queries import html


@mock.patch('gcpdiag.queries.html.requests.get', autospec=True)
class TestFetchAndExtractHtmlContent(unittest.TestCase):
  """Test Fetch and Extract html content"""

  def test_fetch_and_extract_table(self, mock_get):
    with open(
        'test-data/datafusion1/html-content/'
        'version_support_policy.html',
        encoding='utf-8') as fh:
      mock_get.return_value.content = fh.read().encode('utf-8')
      mock_get.return_value.status_code = 200

      test_table = html.fetch_and_extract_table(
          page_url=
          'https://cloud.google.com/data-fusion/docs/support/version-support-policy',
          tag='h2',
          tag_id='support_timelines')
      assert test_table is not None
      assert len(test_table.find_all('tr')) == 10
      assert test_table.find_all('tr')[1].find_all(
          'td')[0].text.strip() == '6.9'
      assert test_table.find_all('tr')

  def test_fetch_and_extract_table_with_no_tag(self, mock_get):
    mock_get.return_value.content = """
      <html>
        <body>
          <table>
            <tr><th>Column 1</th><th>Column2</th></tr>
            <tr><td>Value1</td><td>Value2</td></tr>
          </table>
        </body>
      </html>
    """
    mock_get.return_value.status_code = 200

    test_table = html.fetch_and_extract_table(
        page_url=
        'https://cloud.google.com/data-fusion/docs/support/version-support-policy'
    )
    self.assertIsNone(test_table)

  def test_fetch_and_extract_table_with_no_tag_id_and_class_name(
      self, mock_get):
    mock_get.return_value.content = """
      <html>
        <body>
          <h1>This is a header</h1>
          <table>
            <tr><th>Column 1</th><th>Column2</th></tr>
            <tr><td>Value1</td><td>Value2</td></tr>
          </table>
        </body>
      </html>
    """
    mock_get.return_value.status_code = 200

    test_table = html.fetch_and_extract_table(
        page_url=
        'https://cloud.google.com/data-fusion/docs/support/version-support-policy',
        tag='h1')
    assert test_table is not None
    assert len(test_table.find_all('tr')) == 2

  def test_fetch_and_extract_table_with_class_name(self, mock_get):
    mock_get.return_value.content = """
      <html>
        <body>
          <h1 class="my-table">This is a header</h1>
          <table>
            <tr><th>Column 1</th><th>Column2</th></tr>
            <tr><td>Value1</td><td>Value2</td></tr>
            <tr><td>Value3</td><td>Value4</td></tr>
          </table>
        </body>
      </html>
    """
    mock_get.return_value.status_code = 200

    test_table = html.fetch_and_extract_table(
        page_url=
        'https://cloud.google.com/data-fusion/docs/support/version-support-policy',
        tag='h1',
        class_name='my-table')
    assert test_table is not None
    assert len(test_table.find_all('tr')) == 3
    assert test_table.find_all('tr')[1].find_all(
        'td')[0].text.strip() == 'Value1'

  def test_fetch_and_extract_table_with_tag_id(self, mock_get):
    mock_get.return_value.content = """
      <html>
        <body>
          <h1 id="my-table">This is a header</h1>
          <table>
            <tr><th>Column 1</th><th>Column2</th></tr>
            <tr><td>Value1</td><td>Value2</td></tr>
            <tr><td>Value3</td><td>Value4</td></tr>
          </table>
        </body>
      </html>
    """
    mock_get.return_value.status_code = 200

    test_table = html.fetch_and_extract_table(
        page_url=
        'https://cloud.google.com/data-fusion/docs/support/version-support-policy',
        tag='h1',
        tag_id='my-table')
    assert test_table is not None
    assert len(test_table.find_all('tr')) == 3
    assert test_table.find_all('tr')[2].find_all(
        'td')[1].text.strip() == 'Value4'
