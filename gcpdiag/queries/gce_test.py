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

import concurrent.futures
import re
import unittest
from unittest import mock

from gcpdiag import config, models
from gcpdiag.queries import apigee, apis_stub, gce, network

DATAPROC_LABELS = {'goog-dataproc-cluster-name': 'cluster'}
DUMMY_REGION = 'europe-west4'
DUMMY_ZONE = 'europe-west4-a'
DUMMY_ZONE2 = 'europe-west1-b'
DUMMY_ZONE3 = 'europe-west4-b'
DUMMY_PROJECT_NAME2 = 'gcpdiag-gce-vm-performance'
DUMMY_PROJECT_NAME = 'gcpdiag-gce1-aaaa'
DUMMY_LICENSE_PROJECT_NAME = 'windows-cloud'
DUMMY_PROJECT_NR = '12340001'
DUMMY_DEFAULT_NAME = 'default'
DUMMY_INSTANCE1_NAME = 'gce1'
DUMMY_INSTANCE1_PATH = (f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/'
                        f'instances/{DUMMY_INSTANCE1_NAME}')
DUMMY_INSTANCE1_LABELS = {'foo': 'bar'}
DUMMY_INSTANCE2_NAME = 'gce2'
DUMMY_INSTANCE2_PATH = (f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/'
                        f'instances/{DUMMY_INSTANCE2_NAME}')
DUMMY_INSTANCE2_LABELS = {'gcpdiag-test': 'mig'}
DUMMY_INSTANCE3_NAME = 'gke-gke1-default-pool-35923fbc-2xxp'
DUMMY_INSTANCE3_PATH = (f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE}/'
                        f'instances/{DUMMY_INSTANCE3_NAME}')
DUMMY_INSTANCE3_LABELS = {'gcp_doctor_test': 'gke'}
DUMMY_INSTANCE4_NAME = 'windows-test'

DUMMY_NEG1_NAME = 'neg1'
DUMMY_NEG1_PATH = (f'projects/{DUMMY_PROJECT_NAME}/zones/{DUMMY_ZONE3}/'
                   f'networkEndpointGroups/{DUMMY_NEG1_NAME}')

DUMMY_REGION_MIG_PROJECT_NAME = 'gcpdiag-apigee1-aaaa'
DUMMY_REGION_MIG_NAME = 'mig-bridge-manager-us-central1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGce(unittest.TestCase):
  """Test code in gce.py"""

  def test_get_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    assert len(instances) == 6
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert DUMMY_INSTANCE1_PATH in instances_by_path
    assert (instances_by_path[DUMMY_INSTANCE1_PATH].full_path ==
            DUMMY_INSTANCE1_PATH)
    assert (instances_by_path[DUMMY_INSTANCE1_PATH].short_path ==
            f'{DUMMY_PROJECT_NAME}/{DUMMY_INSTANCE1_NAME}')
    # also verify that the instances dict uses the instance id as key
    assert instances_by_path[DUMMY_INSTANCE1_PATH].id in instances

  def test_get_instances_by_region_returns_instance(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['fake-region', DUMMY_REGION])
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert DUMMY_INSTANCE1_PATH in instances_by_path and len(instances) == 6

  def test_get_instances_by_label(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}

    assert DUMMY_INSTANCE1_PATH in instances_by_path and len(instances) == 1

  def test_get_instances_by_other_region_returns_empty_result(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['fake-region'])
    instances = gce.get_instances(context)
    assert len(instances) == 0

  def test_is_serial_port_logging_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    i = instances_by_path[DUMMY_INSTANCE1_PATH]
    assert i.is_serial_port_logging_enabled()
    assert i.get_metadata('serial-port-logging-enable')

  def test_is_serial_port_logging_enabled_instance_level(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    i = instances_by_path[DUMMY_INSTANCE2_PATH]
    assert not i.is_serial_port_logging_enabled()

  def test_is_gke_node_false(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert not instances_by_path[DUMMY_INSTANCE1_PATH].is_gke_node()

  def test_is_gke_node_true(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE3_LABELS)
    instances = gce.get_instances(context)
    assert len(instances) == 1
    for n in instances.values():
      assert n.is_gke_node()

  def test_is_windows_machine(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert instances_by_path[DUMMY_INSTANCE1_PATH].is_windows_machine() is True
    assert instances_by_path[DUMMY_INSTANCE2_PATH].is_windows_machine() is True

  def test_is_preemptible_vm(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert instances_by_path[DUMMY_INSTANCE1_PATH].is_preemptible_vm is True
    assert instances_by_path[DUMMY_INSTANCE2_PATH].is_preemptible_vm is True
    assert instances_by_path[DUMMY_INSTANCE3_PATH].is_preemptible_vm is False

  def test_min_cpu_platform(self):
    instance = gce.get_instance(DUMMY_PROJECT_NAME, DUMMY_ZONE,
                                DUMMY_INSTANCE1_NAME)
    self.assertEqual(instance.min_cpu_platform(), 'Intel Skylake')
    instance2 = gce.get_instance(DUMMY_PROJECT_NAME, DUMMY_ZONE,
                                 DUMMY_INSTANCE2_NAME)
    self.assertEqual(instance2.min_cpu_platform(), 'None')

  def test_network(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert (instances_by_path[DUMMY_INSTANCE1_PATH].network.name ==
            DUMMY_DEFAULT_NAME)
    assert (instances_by_path[DUMMY_INSTANCE2_PATH].network.name ==
            DUMMY_DEFAULT_NAME)

  def test_tags(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert 'secured-instance' in instances_by_path[DUMMY_INSTANCE1_PATH].tags
    assert 'secured-instance' in instances_by_path[DUMMY_INSTANCE2_PATH].tags

  def test_disks(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert len(instances_by_path[DUMMY_INSTANCE1_PATH].disks) == 1
    assert len(instances_by_path[DUMMY_INSTANCE2_PATH].disks) == 1

  def test_access_scopes(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert set(instances_by_path[DUMMY_INSTANCE1_PATH].access_scopes) == {
        'https://www.googleapis.com/auth/devstorage.read_only',
        'https://www.googleapis.com/auth/logging.write',
        'https://www.googleapis.com/auth/monitoring.write',
        'https://www.googleapis.com/auth/service.management.readonly',
        'https://www.googleapis.com/auth/servicecontrol',
    }

  def test_service_account(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    instances_by_path = {i.full_path: i for i in instances.values()}
    assert (instances_by_path[DUMMY_INSTANCE1_PATH].service_account ==
            f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com')

  def test_get_global_operations(self):
    """get global operations."""
    operations = gce.get_global_operations(project=DUMMY_PROJECT_NAME2)
    assert len(operations) > 0

    for op in operations:
      assert isinstance(op['id'], str)

  def test_get_instance_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['europe-west4'])
    groups = gce.get_instance_groups(context)
    ig1_path = 'projects/gcpdiag-gce1-aaaa/zones/europe-west4-a/instanceGroups/instance-group-1'
    mig_path = 'projects/gcpdiag-gce1-aaaa/zones/europe-west4-a/instanceGroups/mig'
    assert groups[ig1_path].has_named_ports() is True
    assert groups[mig_path].has_named_ports() is False
    assert 'http' in [p['name'] for p in groups[ig1_path].named_ports]
    assert 'https' not in [p['name'] for p in groups[ig1_path].named_ports]

  def test_get_managed_instance_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['europe-west4'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 2
    for n in migs.values():
      if n.name == 'mig':
        assert n.is_gke() is False

  def test_get_region_managed_instance_groups(self):
    context = models.Context(project_id=DUMMY_REGION_MIG_PROJECT_NAME,
                             locations=['us-central1'])
    migs = gce.get_region_managed_instance_groups(context)
    assert len(migs) == 1
    m = next(iter(migs.values()))
    assert m.name == DUMMY_REGION_MIG_NAME
    assert m.template.get_metadata('') == ''
    assert m.template.get_metadata('non-existing') == ''
    assert (m.template.get_metadata('startup-script-url') ==
            apigee.MIG_STARTUP_SCRIPT_URL)

  def test_get_managed_instance_groups_gke(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['europe-west4'])
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 2
    m = next(iter(migs.values()))
    assert m.is_gke() is True

  def test_get_managed_instance_groups_empty_result(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    migs = gce.get_managed_instance_groups(context)
    assert len(migs) == 0

  def test_managed_instance_group_zone(self):
    # zonal mig
    mig1 = gce.ManagedInstanceGroup(
        'p1', {
            'name':
                'mig1',
            'zone':
                'https://www.googleapis.com/compute/v1/projects/p1/zones/us-central1-a',
            'selfLink':
                '...'
        })
    self.assertEqual(mig1.zone, 'us-central1-a')
    # regional mig
    mig2 = gce.ManagedInstanceGroup(
        'p1', {
            'name':
                'mig2',
            'region':
                'https://www.googleapis.com/compute/v1/projects/p1/regions/us-central1',
            'selfLink':
                '...'
        })
    self.assertIsNone(mig2.zone)
    # malformed zone
    mig3 = gce.ManagedInstanceGroup(
        'p1', {
            'name': 'mig3',
            'zone': 'https://www.googleapis.com/compute/v1/projects/p1/zones/',
            'selfLink': '...'
        })
    with self.assertRaises(RuntimeError):
      _ = mig3.zone

  def test_managed_instance_group_get_method(self):
    mig = gce.ManagedInstanceGroup(
        'p1', {
            'name':
                'mig1',
            'zone':
                'https://www.googleapis.com/compute/v1/projects/p1/zones/us-central1-a',
            'selfLink':
                '...',
            'status': {
                'versionTarget': {
                    'isReached': True
                }
            }
        })
    self.assertEqual(mig.get('status.versionTarget.isReached'), True)
    self.assertEqual(mig.get('name'), 'mig1')
    self.assertIsNone(mig.get('foo.bar'))
    self.assertEqual(mig.get('foo.bar', 'default'), 'default')

  def test_autoscaler_get_method(self):
    autoscaler = gce.Autoscaler(
        'p1', {
            'name': 'autoscaler1',
            'selfLink':
                'https://www.googleapis.com/compute/v1/projects/p1/zones/us-central1-a/'
                'autoscalers/autoscaler1',
            'autoscalingPolicy': {
                'mode': 'ON'
            }
        })
    self.assertEqual(autoscaler.name, 'autoscaler1')
    self.assertEqual(
        autoscaler.self_link,
        'https://www.googleapis.com/compute/v1/projects/p1/zones/'
        'us-central1-a/autoscalers/autoscaler1')
    self.assertEqual(autoscaler.full_path,
                     'projects/p1/zones/us-central1-a/autoscalers/autoscaler1')
    self.assertEqual(autoscaler.get('autoscalingPolicy.mode'), 'ON')
    self.assertIsNone(autoscaler.get('foo.bar'))
    self.assertEqual(autoscaler.get('foo.bar', 'default'), 'default')

  def test_mig_property(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE3_LABELS)
    for n in gce.get_instances(context).values():
      assert re.match(r'gke-gke1-default-pool-\w+-grp', n.mig.name)

  def test_mig_property_instance_not_in_mig(self):
    instance = gce.get_instance(DUMMY_PROJECT_NAME, DUMMY_ZONE,
                                DUMMY_INSTANCE1_NAME)
    with self.assertRaises(AttributeError):
      _ = instance.mig

  def test_get_instance_group_manager(self):
    mig = gce.get_instance_group_manager(DUMMY_PROJECT_NAME, DUMMY_ZONE, 'mig')
    self.assertEqual(mig.name, 'mig')
    self.assertEqual(mig.zone, DUMMY_ZONE)

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
    assert len(regions) == 1
    assert 'europe-west4' in [r.name for r in regions]

  def test_count_no_action_instances(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             locations=['europe-west4'])
    migs = gce.get_managed_instance_groups(context)
    # check for number of migs since I am only checking for a single mig in the region
    assert len(migs) == 2

    for m in migs.values():
      print(m)
      count = m.count_no_action_instances()

    assert count == 2

  def test_get_instance_templates(self):
    templates = gce.get_instance_templates(DUMMY_PROJECT_NAME)
    # find the GKE node pool template
    prefix = ('projects/gcpdiag-gce1-aaaa/global/instanceTemplates/'
              'gke-gke1-default-pool')
    matched_names = [t for t in templates if t.startswith(prefix)]
    assert len(matched_names) == 2
    t = templates[matched_names[0]]
    assert t.name.startswith('gke-gke1-default-pool')
    # GKE nodes pools have at least one tag called 'gke-CLUSTERNAME-CLUSTERHASH-node'
    assert any(
        tag.startswith('gke-') and tag.endswith('-node') for tag in t.tags)
    # service_account
    assert (t.service_account ==
            f'{DUMMY_PROJECT_NR}-compute@developer.gserviceaccount.com')

  def test_mig_template(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE2_LABELS)
    for n in {i.mig for i in gce.get_instances(context).values()}:
      assert n.template.name.startswith('mig-')

  def test_get_all_disks(self):
    disks = gce.get_all_disks(models.Context(project_id=DUMMY_PROJECT_NAME))
    for d in disks:
      assert d.bootable is True
      if 'unattached-disk' == d.name:
        assert d.in_use is False
      else:
        assert d.in_use is True

  def test_get_instance(self):
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    assert instance.name == DUMMY_INSTANCE1_NAME

  def test_get_instance_interface_effective_firewalls(self):
    # use default network interface as nic0
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    firewalls = gce.get_instance_interface_effective_firewalls(
        instance=instance, nic='nic0')
    assert isinstance(firewalls, gce.InstanceEffectiveFirewalls)

  def test_is_public_machine(self):
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    assert instance.is_public_machine() is False
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE4_NAME,
    )
    assert instance.is_public_machine() is True

  def test_check_license(self):
    licenses = gce.get_gce_public_licences(DUMMY_LICENSE_PROJECT_NAME)
    payg_licenses = [x for x in licenses if not x.endswith('-byol')]
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    assert instance.check_license(payg_licenses) is True
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE4_NAME,
    )
    assert instance.check_license(payg_licenses) is False

  def test_get_instance_interface_subnetworks(self):
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    for subnetwork in instance.subnetworks:
      assert isinstance(subnetwork, network.Subnetwork)

  def test_get_instance_interface_routes(self):
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    for route in instance.routes:
      assert isinstance(route, network.Route)

  def test_is_vm_running(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    for i in instances.values():
      if i.status == 'RUNNING':
        assert i.is_running
      else:
        assert not i.is_running

  def test_network_interface_count(self):
    instance = gce.get_instance(
        project_id=DUMMY_PROJECT_NAME,
        zone=DUMMY_ZONE,
        instance_name=DUMMY_INSTANCE1_NAME,
    )
    self.assertEqual(instance.network_interface_count, 1)

  def test_get_serial_port_outputs(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    query = gce.get_instances_serial_port_output(context)

    assert len(query) > 0

    assert len(query) > 0

  def test_fetch_serial_port_outputs(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    query = gce.fetch_serial_port_outputs(context=context)

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      gce.execute_fetch_serial_port_outputs(executor)

      # verify that at least one instance serial log (gce2) is present
      all_entries = list(query.entries)

      assert len(all_entries) > 0

  def test_serial_output_contents_order(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    query = gce.get_instances_serial_port_output(context=context)

    gce2_id = '1010101010'
    serial_output = next(iter(query))

    assert gce2_id == serial_output.instance_id  # gce2 output
    assert serial_output.contents

    first_entry = serial_output.contents[0]
    assert ('01H\u001b[=3h\u001b[2J\u001b[01;01HCSM BBS Table full.'
            in first_entry)
    #
    last_entry = serial_output.contents[-1]
    assert '[   20.5] cloud-init[56]: Cloud-init v. 21.4 finished' in last_entry

  def test_is_serial_port_buffer_enabled(self):
    config.init({'enable_gce_serial_buffer': False}, 'x')
    assert not gce.is_serial_port_buffer_enabled()

    config.init({'enable_gce_serial_buffer': True}, 'x')
    assert gce.is_serial_port_buffer_enabled()

  def test_is_dataproc_instance(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DATAPROC_LABELS)
    instances = gce.get_instances(context)
    for i in instances.values():
      assert i.is_dataproc_instance()

    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    for i in instances.values():
      assert not i.is_dataproc_instance()

  def test_get_labels(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             labels=DUMMY_INSTANCE1_LABELS)
    instances = gce.get_instances(context)
    for i in instances.values():
      assert i.labels == DUMMY_INSTANCE1_LABELS

  def test_get_zonal_network_endpoint_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    negs = gce.get_zonal_network_endpoint_groups(context)
    assert len(negs) == 1
    negs_by_path = {i.full_path: i for i in negs.values()}
    assert DUMMY_NEG1_PATH in negs_by_path

  def test_get_instances_by_id(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME,
                             resources=['1010101011'])
    instances = gce.get_instances(context)
    self.assertEqual(len(instances), 1)
    self.assertEqual(list(instances.values())[0].name, 'gce2')
