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

import re
from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gce

DUMMY_REGION = 'europe-west4'
DUMMY_ZONE = 'europe-west4-a'
DUMMY_PROJECT_NAME = 'gcpdiag-gce1-aaaa'
DUMMY_PROJECT_NR = '12340001'
DUMMY_DEFAULT_NAME = 'default'
DUMMY_INSTANCE1_NAME = 'gce1'
DUMMY_INSTANCE1_LABELS = {'foo': 'bar'}
DUMMY_INSTANCE2_NAME = 'gce2'
DUMMY_INSTANCE3_LABELS = {'gcp_doctor_test': 'gke'}


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGce:
  """Test code in gce.py"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    assert len(instances) == 8
    instances_by_name = {i.name: i for i in instances.values()}
    assert DUMMY_INSTANCE1_NAME in instances_by_name
    assert instances_by_name[DUMMY_INSTANCE1_NAME].full_path == \
        f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/instances/{DUMMY_INSTANCE1_NAME}'
    assert instances_by_name[DUMMY_INSTANCE1_NAME].short_path == \
        f'{DUMMY_PROJECT_NAME}/{DUMMY_INSTANCE1_NAME}'
    # also verify that the instances dict uses the instance id as key
    assert instances_by_name[DUMMY_INSTANCE1_NAME].id in instances

  def test_get_instances_by_region_returns_instance(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['fake-region', DUMMY_REGION])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert DUMMY_INSTANCE1_NAME in instances_by_name and len(instances) == 4

  def test_get_instances_by_label(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert DUMMY_INSTANCE1_NAME in instances_by_name and len(instances) == 1

  def test_get_instances_by_other_region_returns_empty_result(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['fake-region'])
    instances = gce.get_instances(context)
    assert len(instances) == 0

  def test_is_serial_port_logging_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    i = instances_by_name[DUMMY_INSTANCE1_NAME]
    assert i.is_serial_port_logging_enabled()
    assert i.get_metadata('serial-port-logging-enable')

  def test_is_serial_port_logging_enabled_instance_level(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    i = instances_by_name[DUMMY_INSTANCE2_NAME]
    assert not i.is_serial_port_logging_enabled()

  def test_is_gke_node_false(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert not instances_by_name[DUMMY_INSTANCE1_NAME].is_gke_node()

  def test_is_gke_node_true(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE3_LABELS])
    instances = gce.get_instances(context)
    assert len(instances) == 4
    for n in instances.values():
      assert n.is_gke_node()

  def test_is_windows_machine(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert instances_by_name[DUMMY_INSTANCE1_NAME].is_windows_machine() is True
    assert instances_by_name[DUMMY_INSTANCE2_NAME].is_windows_machine() is False

  def test_network(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert instances_by_name[
        DUMMY_INSTANCE1_NAME].network.name == DUMMY_DEFAULT_NAME
    assert instances_by_name[
        DUMMY_INSTANCE2_NAME].network.name == DUMMY_DEFAULT_NAME

  def test_tags(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert 'secured-instance' in instances_by_name[DUMMY_INSTANCE1_NAME].tags
    assert 'secured-instance' in instances_by_name[DUMMY_INSTANCE2_NAME].tags

  def test_access_scopes(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert set(instances_by_name[DUMMY_INSTANCE1_NAME].access_scopes) == {
        'https://www.googleapis.com/auth/devstorage.read_only',
        'https://www.googleapis.com/auth/logging.write',
        'https://www.googleapis.com/auth/monitoring.write',
        'https://www.googleapis.com/auth/service.management.readonly',
        'https://www.googleapis.com/auth/servicecontrol'
    }

  def test_service_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE1_LABELS])
    instances = gce.get_instances(context)
    instances_by_name = {i.name: i for i in instances.values()}
    assert instances_by_name[
        DUMMY_INSTANCE1_NAME].service_account == \
          f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com'

  def test_get_instance_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             regions=['europe-west4'])
    groups = gce.get_instance_groups(context)
    assert groups['instance-group-1'].has_named_ports() is True
    assert groups['mig'].has_named_ports() is False
    assert 'http' in [p['name'] for p in groups['instance-group-1'].named_ports]
    assert 'https' not in [
        p['name'] for p in groups['instance-group-1'].named_ports
    ]

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
      assert re.match(r'gke-gke1-default-pool-\w+-grp', n.mig.name)

  def test_get_all_regions(self):
    regions = gce.get_all_regions(DUMMY_PROJECT_NAME)
    assert len(regions) > 0
    assert 'us-east1' in [r.name for r in regions]
    assert 'europe-north1' in [r.name for r in regions]
    assert 'asia-southeast1' in [r.name for r in regions]
    assert 'southamerica-east1' in [r.name for r in regions]

  def test_get_regions_with_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    regions = gce.get_regions_with_instances(context)
    assert len(regions) == 2
    assert 'europe-west1' in [r.name for r in regions]

  def test_get_instance_templates(self):
    templates = gce.get_instance_templates(DUMMY_PROJECT_NAME)
    # find the GKE node pool template
    matched_names = [
        t for t in templates if t.startswith('gke-gke1-default-pool')
    ]
    assert len(matched_names) == 1
    t = templates[matched_names[0]]
    assert t.name.startswith('gke-gke1-default-pool')
    # GKE nodes pools have at least one tag called 'gke-CLUSTERNAME-CLUSTERHASH-node'
    assert [
        True for tag in t.tags
        if tag.startswith('gke-') and tag.endswith('-node')
    ]
    # service_account
    assert t.service_account == f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com'

  def test_mig_template(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=[DUMMY_INSTANCE3_LABELS])
    for n in {i.mig for i in gce.get_instances(context).values()}:
      assert n.template.name.startswith('gke-')
