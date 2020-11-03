# Lint as: python3
"""lint command: find potential issues in GCP projects."""

import enum

import dataclasses
from gcp_doctor import models


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
  """Identifies a lint finding (issue)."""
  context: models.Context
  test: LintTest
  findings: list

  def __init__(self, context: models.Context, test: LintTest):
    self.context = context
    self.test = test
    self.findings = []

  def __iter__(self):
    return self.findings.__iter__()
