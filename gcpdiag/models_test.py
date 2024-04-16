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
    models.Context(project_id='project1', locations='us-central1-b')


def test_context_to_string():
  """Verify stringification of Context with and without regions/labels."""
  c = models.Context(project_id='project1')
  assert str(c) == 'project: project1, parameters: {project_id=project1}'

  c = models.Context(project_id='project1', locations=[])
  assert str(c) == 'project: project1, parameters: {project_id=project1}'

  c = models.Context(project_id='project1', locations=['us-central1'])
  assert str(c) == (
      'project: project1, locations (regions/zones): us-central1, '
      'parameters: {project_id=project1}')

  c = models.Context(project_id='project1',
                     locations=['us-west1', 'us-west2'],
                     resources=['dev-1', 'prod-1'])
  assert str(c) == (
      'project: project1, resources: dev-1|prod-1, locations '
      '(regions/zones): us-west1|us-west2, parameters: {project_id=project1}')

  c = models.Context(project_id='project1', labels={'A': 'B', 'X': 'Y'})
  assert str(
      c
  ) == 'project: project1, labels: {A=B,X=Y}, parameters: {project_id=project1}'

  c = models.Context(project_id='project1',
                     locations=['us-central1'],
                     labels={'X': 'Y'},
                     resources=['name'])
  assert str(c) == (
      'project: project1, resources: name, locations (regions/zones): us-central1, '
      'labels: {X=Y}, parameters: {project_id=project1}')


def test_match_project_resource():
  """Verify Context matching evaluations"""

  # common use case simply lint one resource.
  c = models.Context(project_id='project1', resources=['gke-prod'])
  assert c.match_project_resource(resource='gke-prod', location='', labels={})
  assert c.match_project_resource(resource='gke-prod',
                                  location='us-central1',
                                  labels={'X': 'Y'})
  assert not c.match_project_resource(
      resource='', location='us-central1', labels={'X': 'Y'})

  # More complex context scope
  c = models.Context(project_id='project1',
                     locations=['us-central1', 'us-central2'],
                     labels={
                         'X': 'Y',
                         'A': 'B'
                     },
                     resources=['dev-*', '^bastion-(host|machine)$'])

  assert c.match_project_resource(resource='bastion-host',
                                  location='us-central1',
                                  labels={'X': 'Y'})
  assert c.match_project_resource(resource='dev-frontend',
                                  location='us-central1',
                                  labels={'X': 'Y'})
  assert c.match_project_resource(resource='dev-backend',
                                  location='us-central1',
                                  labels={'X': 'Y'})
  assert not c.match_project_resource(
      resource='', location='us-central1', labels={'X': 'Y'})
  assert not c.match_project_resource(
      resource='bastion-host', location='', labels={'X': 'Y'})
  assert not c.match_project_resource(
      resource='bastion-host', location='us-central1', labels={'X': 'B'})
  assert not c.match_project_resource(
      resource='name', labels={'X': 'Y'}, location='us-central3')
  assert not c.match_project_resource(
      location='us-central3', labels={'X': 'Y'}, resource='uninterested-name')
  assert not c.match_project_resource(resource='', location='', labels={})

  # allow some products to ignore locations or labels if there are tricky to support
  assert c.match_project_resource(resource='bastion-host')
  assert c.match_project_resource(resource='BASTION-machine')

  assert c.match_project_resource(resource='dev-backend', labels={'X': 'Y'})
  assert c.match_project_resource(resource='dev-frontend', labels={'X': 'Y'})
  # Zones under a region should be considered if user set's on it's region
  assert c.match_project_resource(resource='bastion-host',
                                  location='us-central2-a')

  # Test IGNORELOCATION AND IGNORELABEL
  assert c.match_project_resource(resource='bastion-host',
                                  location=c.IGNORELOCATION,
                                  labels=c.IGNORELABEL)

  # If for some strange coincidence customer's label is IGNORELABEL evaluation
  # should fail if it doesn't match context.
  assert not c.match_project_resource(resource='bastion-host',
                                      labels={'IGNORELABEL': 'IGNORELABEL'})


def test_generic_declaration():
  param = models.Parameter({'key': True})
  assert param.get('key')


def test_string_strip_and_lowercase():
  param = models.Parameter()
  param['bool_value_true'] = ' TRUE '
  assert param['bool_value_true'] == 'true'


def test_update_method():
  param = models.Parameter()
  updates = {'new_string': 'world'}
  param.update(updates)
  assert param['new_string'] == 'world'


def test_setdefault_existing_key():
  param = models.Parameter({'existing_key': '100'})
  old_val = param.setdefault('existing_key', '200')
  assert old_val == '100'


def test_setdefault_non_existing_key():
  param = models.Parameter()
  param.setdefault('new_key', '300')
  assert param['new_key'] == '300'
