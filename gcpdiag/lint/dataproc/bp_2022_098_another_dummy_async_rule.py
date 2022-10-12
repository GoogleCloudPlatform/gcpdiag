"""Another dummy async rule

Another dummy async rule
"""

import asyncio

from gcpdiag import lint, models


class FakeResource(models.Resource):

  def __init__(self, text):
    super().__init__(project_id=None)
    self.text = text

  @property
  def full_path(self):
    return self.text


# pylint: disable=unused-argument
async def async_run_rule(context: models.Context,
                         report: lint.LintReportRuleInterface) -> None:
  # Some async sleep calls to pretend we're doing some work
  await asyncio.sleep(1)
  report.add_ok(FakeResource(text='fake resource 4'), 'test ok')
  await asyncio.sleep(1)
  report.add_skipped(FakeResource(text='fake resource 5'), 'test skipped')
  await asyncio.sleep(1)
  report.add_failed(FakeResource(text='fake resource 6'), 'test failed')
