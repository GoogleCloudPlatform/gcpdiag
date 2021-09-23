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

# Lint as: python3
"""Unit tests for test.py."""

import pytest

from gcpdiag import models


def test_context_region_exception():
  """Context constructor with non-list regions should raise an exception."""
  with pytest.raises(ValueError):
    models.Context(project_id='project1', regions='us-central1-b')


def test_context_to_string():
  """Verify stringification of Context with and without regions/labels."""
  c = models.Context(project_id='project1')
  assert str(c) == 'project: project1'

  c = models.Context(project_id='project1', regions=[])
  assert str(c) == 'project: project1'

  c = models.Context(project_id='project1', regions=['us-central1'])
  assert str(c) == 'project: project1, regions: us-central1'

  c = models.Context(project_id='project1',
                     labels=[{
                         'A': 'B',
                         'X': 'Y'
                     }, {
                         'foo': 'bar'
                     }])
  assert str(c) == 'project: project1, labels: {A=B,X=Y},{foo=bar}'

  c = models.Context(project_id='project1',
                     regions=['us-central1'],
                     labels=[{
                         'X': 'Y'
                     }])
  assert str(c) == 'project: project1, regions: us-central1, labels: {X=Y}'
