"""Dummy async rule

Dummy async rule
"""

import asyncio

from gcpdiag import lint, models


# pylint: disable=unused-argument
async def async_run_rule(context: models.Context,
                         report: lint.LintReportRuleInterface) -> None:
  await asyncio.sleep(3)
  report.add_skipped(None, 'no dataproc clusters found')

  # report.add_skipped(None, 'no dataproc clusters found')
  # report.add_ok(cluster)
  # report.add_failed(cluster)
