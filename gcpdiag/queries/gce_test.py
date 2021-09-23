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
"""Test code in gce.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gce

DUMMY_REGION = 'europe-west4'
DUMMY_ZONE = 'europe-west4-a'
DUMMY_PROJECT_NAME = 'gcpd-gce1-4exv'
DUMMY_PROJECT_NR = '50670056743'
DUMMY_INSTANCE1_ID = '48322001635889308'
DUMMY_INSTANCE1_NAME = 'gce1'
DUMMY_INSTANCE1_LABELS = {'foo': 'bar'}
DUMMY_INSTANCE2_ID = '7817880697222713500'
DUMMY_INSTANCE2_NAME = 'gce2'
DUMMY_INSTANCE3_LABELS = {'gcp_doctor_test': 'gke'}


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGce:
  """Test code in gce.py"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    assert len(instances) == 8
    assert DUMMY_INSTANCE1_ID in instances
    assert instances[DUMMY_INSTANCE1_ID].full_path == \
        f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/instances/{DUMMY_INSTANCE1_NAME}'
    assert instances[DUMMY_INSTANCE1_ID].short_path == \
        f'{DUMMY_PROJECT_NAME}/{DUMMY_INSTANCE1_NAME}'

  def test_get_instances_by_region_returns_instance(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['fake-region', DUMMY_REGION])
    instances = gce.get_instances(context)
    assert DUMMY_INSTANCE1_ID in instances and len(instances) == 4

  def test_get_instances_by_label(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert DUMMY_INSTANCE1_ID in instances and len(instances) == 1

  def test_get_instances_by_other_region_returns_empty_result(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['fake-region'])
    instances = gce.get_instances(context)
    assert len(instances) == 0

  def test_is_gke_node_false(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert not instances[DUMMY_INSTANCE1_ID].is_gke_node()

  def test_is_gke_node_true(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE3_LABELS])
    instances = gce.get_instances(context)
    assert len(instances) == 4
    for n in instances.values():
      assert n.is_gke_node()

  def test_service_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert instances[
        DUMMY_INSTANCE1_ID].service_account == \
          f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com'

  def test_get_managed_instance_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['europe-west4'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 1
    m = next(iter(migs.values()))
    assert m.name == 'mig'
    assert m.is_gke() is False

  def test_get_managed_instance_groups_gke(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['europe-west1'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 1
    m = next(iter(migs.values()))
    assert m.is_gke() is True

  def test_get_managed_instance_groups_empty_result(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 0

  def test_mig_property(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE3_LABELS])
    for n in gce.get_instances(context).values():
      assert n.mig.name == 'gke-gke1-default-pool-564e261a-grp'

  def test_is_serial_port_logging_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    i = instances[DUMMY_INSTANCE1_ID]
    assert i.is_serial_port_logging_enabled()
    assert i.get_metadata('serial-port-logging-enable')

  def test_is_serial_port_logging_enabled_instance_level(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    i = instances[DUMMY_INSTANCE2_ID]
    assert not i.is_serial_port_logging_enabled()
