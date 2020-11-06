# Lint as: python3
"""lint command: find potential issues in GCP projects."""

import dataclasses
import enum


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
  findings: list

  def __init__(self):
    self.findings = []

  def __iter__(self):
    return self.findings.__iter__()
