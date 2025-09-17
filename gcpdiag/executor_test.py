# Copyright 2025 Google LLC
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
"""Unit tests for executor.py."""

import unittest
from unittest import mock

from gcpdiag import executor, models


class ContextAwareExecutorTest(unittest.TestCase):

  def test_context_propagation_with_submit(self):
    """Test that context is setup and torn down with submit()."""
    mock_provider = mock.Mock()
    mock_context = mock.Mock(spec=models.Context)
    mock_context.context_provider = mock_provider

    with executor.ContextAwareExecutor(context=mock_context) as ex:
      future = ex.submit(lambda: 'test')
      self.assertEqual('test', future.result())

    mock_provider.setup_thread_context.assert_called_once()
    mock_provider.teardown_thread_context.assert_called_once()

  def test_context_propagation_with_map(self):
    """Test that context is setup and torn down with map()."""
    mock_provider = mock.Mock()
    mock_context = mock.Mock(spec=models.Context)
    mock_context.context_provider = mock_provider

    with executor.ContextAwareExecutor(context=mock_context) as ex:
      results = list(ex.map(lambda x: x, ['test']))
      self.assertEqual(['test'], results)

    mock_provider.setup_thread_context.assert_called_once()
    mock_provider.teardown_thread_context.assert_called_once()


if __name__ == '__main__':
  unittest.main()
