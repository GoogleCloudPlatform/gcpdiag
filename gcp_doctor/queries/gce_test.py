# Lint as: python3
"""Test code in gce.py."""

from unittest import mock

from gcp_doctor import models
from gcp_doctor.queries import gce, gce_stub

DUMMY_REGION = 'europe-west4'
DUMMY_ZONE = 'europe-west4-a'
DUMMY_PROJECT_NAME = 'gcpd-gce1-4exv'
DUMMY_PROJECT_NR = '50670056743'
DUMMY_INSTANCE1_ID = '5095970208757295818'
DUMMY_INSTANCE1_NAME = 'gce1'
DUMMY_INSTANCE1_LABELS = {'foo': 'bar'}
DUMMY_INSTANCE2_ID = '7608219626705758859'
DUMMY_INSTANCE2_NAME = 'gce2'
DUMMY_INSTANCE3_LABELS = {'gcp_doctor_test': 'gke'}


@mock.patch('gcp_doctor.queries.apis.get_api', new=gce_stub.get_api_stub)
class TestGce:
  """Test code in gce.py"""

  def test_get_instances(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME])
    instances = gce.get_instances(context)
    assert len(instances) == 6
    assert DUMMY_INSTANCE1_ID in instances
    assert instances[DUMMY_INSTANCE1_ID].full_path == \
        f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/instances/{DUMMY_INSTANCE1_NAME}'
    assert instances[DUMMY_INSTANCE1_ID].short_path == \
        f'{DUMMY_PROJECT_NAME}/{DUMMY_INSTANCE1_NAME}'

  def test_get_instances_by_region_returns_instance(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             regions=['fake-region', DUMMY_REGION])
    instances = gce.get_instances(context)
    assert DUMMY_INSTANCE1_ID in instances and len(instances) == 2

  def test_get_instances_by_label(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert DUMMY_INSTANCE1_ID in instances and len(instances) == 1

  def test_get_instances_by_other_region_returns_empty_result(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             regions=['fake-region'])
    instances = gce.get_instances(context)
    assert len(instances) == 0

  def test_is_gke_node_false(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert not instances[DUMMY_INSTANCE1_ID].is_gke_node()

  def test_is_gke_node_true(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_INSTANCE3_LABELS])
    instances = gce.get_instances(context)
    assert len(instances) == 4
    for n in instances.values():
      assert n.is_gke_node()

  def test_service_account(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    assert instances[
        DUMMY_INSTANCE1_ID].service_account == \
          f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com'

  def test_get_managed_instance_groups(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             regions=['europe-west4'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 1
    m = next(iter(migs.values()))
    assert m.name == 'mig'
    assert m.is_gke() is False

  def test_get_managed_instance_groups_gke(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             regions=['europe-west1'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 1
    m = next(iter(migs.values()))
    assert m.is_gke() is True

  def test_get_managed_instance_groups_empty_result(self):
    context = models.Context(projects=[DUMMY_PROJECT_NAME],
                             labels=[DUMMY_INSTANCE1_LABELS])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 0
