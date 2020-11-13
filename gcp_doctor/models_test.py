# Lint as: python3
"""Unit tests for test.py."""

import pytest

from gcp_doctor import models


def test_context_mandatory_projects():
  """Context constructor with empty project list should raise an exception."""
  with pytest.raises(ValueError):
    models.Context(projects=[])


def test_context_region_exception():
  """Context constructor with non-list regions should raise an exception."""
  with pytest.raises(ValueError):
    models.Context(projects=['project1'], regions='us-central1-b')


def test_context_to_string():
  """Verify stringification of Context with and without regions/labels."""
  c = models.Context(projects=['project1', 'project2'])
  assert str(c) == 'projects: project1,project2'

  c = models.Context(projects=['project1', 'project2'], regions=[])
  assert str(c) == 'projects: project1,project2'

  c = models.Context(projects=['project1', 'project2'], regions=['us-central1'])
  assert str(c) == 'projects: project1,project2, regions: us-central1'

  c = models.Context(projects=['project1', 'project2'], labels={'X': 'Y'})
  assert str(c) == 'projects: project1,project2, labels: X=Y'

  c = models.Context(projects=['project1', 'project2'],
                     regions=['us-central1'],
                     labels={'X': 'Y'})
  assert str(
      c) == 'projects: project1,project2, regions: us-central1, labels: X=Y'
