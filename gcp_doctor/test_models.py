# Lint as: python3
"""Unit tests for test.py."""

import pytest

from gcp_doctor import models


def test_context_mandatory_project_list():
  with pytest.raises(ValueError):
    models.Context(project_list=[])


def test_context_region_exception():
  with pytest.raises(ValueError):
    models.Context(project_list=['project1'], regions_list='us-central1-b')


def test_context_to_string():
  c = models.Context(project_list=['project1', 'project2'])
  assert str(c) == 'projects: project1,project2'

  c = models.Context(project_list=['project1', 'project2'], regions_list=[])
  assert str(c) == 'projects: project1,project2'

  c = models.Context(project_list=['project1', 'project2'],
                     regions_list=['us-central1'])
  assert str(c) == 'projects: project1,project2, regions: us-central1'

  c = models.Context(project_list=['project1', 'project2'],
                     labels_list=['labelX'])
  assert str(c) == 'projects: project1,project2, labels: labelX'

  c = models.Context(project_list=['project1', 'project2'],
                     regions_list=['us-central1'],
                     labels_list=['labelX'])
  assert str(
      c) == 'projects: project1,project2, regions: us-central1, labels: labelX'
