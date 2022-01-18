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
"""Test code in network.py."""

import ipaddress
from unittest import mock

from gcpdiag.queries import apis_stub, network

DUMMY_PROJECT_ID = 'gcpdiag-fw-policy-aaaa'
DUMMY_DEFAULT_NETWORK = 'default'
DUMMY_DEFAULT_SUBNET = 'default'
DUMMY_GKE_PROJECT_ID = 'gcpdiag-gke1-aaaa'
DUMMY_GKE_REGION = 'europe-west4'
DUMMY_GKE_SUBNET = 'gke1-subnet'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestNetwork:
  """Test network.Network."""

  def test_get_network(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    assert net.name == DUMMY_DEFAULT_NETWORK
    assert net.full_path == 'projects/gcpdiag-fw-policy-aaaa/global/networks/default'
    assert net.short_path == f'{DUMMY_PROJECT_ID}/default'
    assert net.self_link == \
        f'https://www.googleapis.com/compute/v1/projects/{DUMMY_PROJECT_ID}/global/networks/default'

  def test_subnetworks(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    expected_subnet_url = (
        f'https://www.googleapis.com/compute/v1/projects/{DUMMY_PROJECT_ID}/'
        'regions/europe-west4/subnetworks/default')
    assert expected_subnet_url in net.subnetworks
    assert isinstance(net.subnetworks[expected_subnet_url].ip_network,
                      ipaddress.IPv4Network)

  def test_cluster_subnetwork(self):
    subnet = network.get_subnetwork(project_id=DUMMY_GKE_PROJECT_ID,
                                    region=DUMMY_GKE_REGION,
                                    subnetwork_name=DUMMY_GKE_SUBNET)
    assert subnet.name == DUMMY_GKE_SUBNET
    assert subnet.ip_network == ipaddress.ip_network('192.168.0.0/24')

  def test_get_routers(self):
    net = network.get_network(project_id=DUMMY_GKE_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    sub1 = network.get_subnetwork(project_id=DUMMY_GKE_PROJECT_ID,
                                  region=DUMMY_GKE_REGION,
                                  subnetwork_name=DUMMY_GKE_SUBNET)
    sub2 = network.get_subnetwork(project_id=DUMMY_GKE_PROJECT_ID,
                                  region=DUMMY_GKE_REGION,
                                  subnetwork_name=DUMMY_DEFAULT_SUBNET)
    router = network.get_router(project_id=DUMMY_GKE_PROJECT_ID,
                                region=DUMMY_GKE_REGION,
                                network=net)
    assert router.name == 'gke-default-router'
    assert router.subnet_has_nat(sub1) is False
    assert router.subnet_has_nat(sub2) is True

  def test_ingress_deny(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_address('10.0.0.1'),  #
        ip_protocol='tcp',
        port=21)
    assert r.action == 'deny'
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.0.0.0/24'),  #
        ip_protocol='tcp',
        port=21)
    assert r.action == 'deny'

  def test_ingress_deny_2(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/29'),  #
        ip_protocol='tcp',
        port=1001)
    assert r.action == 'deny'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-800'

  def test_ingress_deny_3(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    # a supernet of src_ip for a deny rule should also match
    # (because we want to catch when a fw rule partially blocks
    # a connection).
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.0.0.0/8'),  #
        ip_protocol='tcp',
        port=1001)
    assert r.action == 'deny'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-800'

  def test_ingress_allow_src_ip(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/29'),  #
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_src_ip_subnet(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/30'),  #
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_source_tags(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        source_tags=['foo'],
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_target_tags(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_address('192.168.1.1'),  #
        target_tags=['bar'],
        ip_protocol='tcp',
        port=1234)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-903'

  def test_ingress_allow_source_sa(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        source_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com',
        ip_protocol='tcp',
        port=4000)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-901'

  def test_ingress_allow_target_sa(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        target_tags=['foo'],
        ip_protocol='tcp',
        port=4000)
    assert r.action == 'allow'

  def test_ingress_parent_policy_allow(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),  #
        ip_protocol='tcp',
        port=2001)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: parent-folder-policy'

  def test_ingress_sub_policy_allow(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),  #
        ip_protocol='tcp',
        port=2003)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_ingress_sub_policy_allow_target_sa(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com')
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_ingress_sub_policy_deny_wrong_target_sa(self):
    net = network.get_network(project_id=DUMMY_PROJECT_ID,
                              network_name=DUMMY_DEFAULT_NETWORK)
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account='foobar@compute-system.iam.gserviceaccount.com')
    assert r.action == 'deny'
