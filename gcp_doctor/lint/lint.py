# Lint as: python3

from gcp_doctor import models

import enum
import dataclasses


class LintTestClass(enum.Enum):
  ERR = 1
  BP = 2


@dataclasses.dataclass
class LintTest:
  """Identifies a lint test."""
  product: str
  level: LintTestClass
  id: str


class LintFindings:
  context: models.Context
  test: LintTest
  findings: list

  def __init__(self, context: models.Context, test: LintTest):
    self.context = context
    self.test = test
    self.findings = []

  def __iter__(self):
    return self.findings.__iter__()
