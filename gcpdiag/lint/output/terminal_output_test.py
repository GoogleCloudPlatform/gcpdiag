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

"""Test code in terminal_output.py."""

import io
import sys
from unittest import mock

from gcpdiag import lint, models
from gcpdiag.lint.output import terminal_output

class TestTerminalOutput:
  """Unit tests for TerminalOutput."""

  def test_display_footer_colored(self):
    # Mock LintResults
    mock_results = mock.Mock(spec=lint.LintResults)
    mock_results.get_totals_by_status.return_value = {
        'skipped': 5,
        'ok': 10,
        'failed': 2
    }

    # Capture stdout
    stdout = io.StringIO()
    output = terminal_output.TerminalOutput(file=stdout)

    # Mock terminal to ensure coloring is "applied" (simulated by wrappers)
    # We can't easily force blessings to colorize in test without a TTY,
    # but we can verify the logic calls the color methods.

    # Actually, blessings.Terminal() detects TTY. We can mock it.
    mock_term = mock.Mock()
    mock_term.yellow = lambda s: f'YELLOW({s})'
    mock_term.green = lambda s: f'GREEN({s})'
    mock_term.red = lambda s: f'RED({s})'
    output.term = mock_term

    output.display_footer(mock_results)

    expected = "Rules summary: YELLOW(5 skipped), GREEN(10 ok), RED(2 failed)\n"
    assert stdout.getvalue() == expected

  def test_display_footer_no_items(self):
    mock_results = mock.Mock(spec=lint.LintResults)
    mock_results.get_totals_by_status.return_value = {}

    stdout = io.StringIO()
    output = terminal_output.TerminalOutput(file=stdout)

    mock_term = mock.Mock()
    output.term = mock_term

    output.display_footer(mock_results)

    # Logic: if count > 0 apply color. if 0, no color.
    # 0 skipped, 0 ok, 0 failed
    expected = "Rules summary: 0 skipped, 0 ok, 0 failed\n"
    assert stdout.getvalue() == expected
