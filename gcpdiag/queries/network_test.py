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
import re
from unittest import mock

from boltons.iterutils import get_path

from gcpdiag import models
from gcpdiag.queries import apis_stub, network

DUMMY_PROJECT_ID = 'gcpdiag-fw-policy-aaaa'
DUMMY_DEFAULT_NETWORK = 'default'
DUMMY_DEFAULT_SUBNET = 'default'
DUMMY_GKE_PROJECT_ID = 'gcpdiag-gke1-aaaa'
DUMMY_GCE_PROJECT_ID = 'gcpdiag-gce1-aaaa'
DUMMY_GKE_REGION = 'europe-west4'
DUMMY_GKE_SUBNET = 'gke1-subnet'
DUMMY_SERVICE_ACCOUNT = 'gke1sa@gcpdiag-gke1-aaaa.iam.gserviceaccount.com'
DUMMY_VPC_PROJECT_ID = 'gcpdiag-vpc1-aaaa'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestNetwork:
  """Test network.Network."""

  def test_get_network(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    assert net.name == DUMMY_DEFAULT_NETWORK
    assert net.full_path == 'projects/gcpdiag-fw-policy-aaaa/global/networks/default'
    assert net.short_path == f'{DUMMY_PROJECT_ID}/default'
    assert net.self_link == \
        f'https://www.googleapis.com/compute/v1/projects/{DUMMY_PROJECT_ID}/global/networks/default'

  def test_subnetworks(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
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

  def test_cluster_subnetwork_iam_policy(self):
    policy = network.get_subnetwork_iam_policy(project_id=DUMMY_GKE_PROJECT_ID,
                                               region=DUMMY_GKE_REGION,
                                               subnetwork_name=DUMMY_GKE_SUBNET)
    assert policy.has_role_permissions(
        f'serviceAccount:{DUMMY_SERVICE_ACCOUNT}', 'roles/compute.networkUser')
    assert not policy.has_role_permissions(
        f'serviceAccount:{DUMMY_SERVICE_ACCOUNT}', 'roles/compute.networkAdmin')

  def test_get_routers(self):
    net = network.get_network(
        project_id=DUMMY_GKE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GKE_PROJECT_ID))
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
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
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
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/29'),  #
        ip_protocol='tcp',
        port=1001)
    assert r.action == 'deny'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-800'

  def test_ingress_deny_3(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
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
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/29'),  #
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_src_ip_subnet(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.100.0.16/30'),  #
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_source_tags(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        source_tags=['foo'],
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-900'

  def test_ingress_allow_target_tags(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_address('192.168.1.1'),  #
        target_tags=['bar'],
        ip_protocol='tcp',
        port=1234)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-903'

  def test_ingress_allow_source_sa(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        source_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com',
        ip_protocol='tcp',
        port=4000)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-901'

  def test_ingress_allow_target_sa(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        target_tags=['foo'],
        ip_protocol='tcp',
        port=4000)
    assert r.action == 'allow'

  def test_ingress_parent_policy_allow(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),  #
        ip_protocol='tcp',
        port=2001)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: parent-folder-policy'

  def test_ingress_sub_policy_allow(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),  #
        ip_protocol='tcp',
        port=2003)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_ingress_sub_policy_allow_target_sa(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com')
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_ingress_sub_policy_deny_wrong_target_sa(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account='foobar@compute-system.iam.gserviceaccount.com')
    assert r.action == 'deny'

  def test_get_ingress_rules(self):
    net = network.get_network(
        project_id=DUMMY_GKE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GKE_PROJECT_ID))
    pattern = re.compile(r'k8s-fw-l7-.*')
    rules = net.firewall.get_vpc_ingress_rules(
        name_pattern=pattern, target_tags=['gke-gke4-3520a9df-node'])
    assert 'gke-gke4-3520a9df-node' in rules[0].target_tags
    assert ipaddress.IPv4Network('130.211.0.0/22') in rules[0].source_ranges

    pattern = re.compile(r'default-allow-.*')
    rules = net.firewall.get_vpc_ingress_rules(name_pattern=pattern)
    assert 'default-allow-rdp' in [r.name for r in rules]
    assert 'default-allow-ssh' in [r.name for r in rules]
    assert 'default-allow-internal' in [r.name for r in rules]
    assert 'default-allow-icmp' in [r.name for r in rules]

    rules = net.firewall.get_vpc_ingress_rules(name='gke-gke6-44734575-ssh')
    assert 'gke-gke6-44734575-ssh' == rules[0].name
    assert 'tcp' == rules[0].allowed[0]['IPProtocol']
    assert '22' in rules[0].allowed[0]['ports']

    rules = net.firewall.get_vpc_ingress_rules(name='not-existing-rule')
    assert 'gke-gke3-b46b134d-ssh' not in [r.name for r in rules]

  def test_egress_deny(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_address('10.0.0.1'),  #
        ip_protocol='tcp',
        port=21)
    assert r.action == 'deny'
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.0.0.0/24'),  #
        ip_protocol='tcp',
        port=21)
    assert r.action == 'deny'

  def test_egress_deny_2(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('142.250.125.95/32'),  #
        ip_protocol='tcp',
        port=1001)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-925'

  def test_egress_deny_3(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.0.0.0/8'),  #
        ip_protocol='tcp',
        port=1001)
    assert r.action == 'deny'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-950'

  def test_egress_allow_src_ip(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('35.190.247.13/32'),  #
        ip_protocol='tcp',
        port=1688)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-1000'

  def test_egress_allow_src_ip_subnet(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.100.0.16/30'),  #
        ip_protocol='tcp',
        port=1006)
    assert r.action == 'deny'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-950'

  def test_egress_allow_source_tags(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('45.100.0.0/24'),  #
        source_tags=['foo'],
        ip_protocol='tcp',
        port=2033)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-1050'

  def test_egress_allow_target_tags(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_address('192.168.1.1'),  #
        target_tags=['bar'],
        ip_protocol='tcp',
        port=1234)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-1025'

  def test_egress_allow_source_sa(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.200.0.16/29'),  #
        source_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com',
        ip_protocol='tcp',
        port=4000)
    assert r.action == 'allow'
    assert r.matched_by_str == 'vpc firewall rule: fw-test-1075'

  def test_egress_parent_policy_allow(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),  #
        ip_protocol='tcp',
        port=2001)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: parent-folder-policy'

  def test_egress_sub_policy_allow(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2003)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_egress_sub_policy_allow_target_sa(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account=
        'service-12340002@compute-system.iam.gserviceaccount.com')
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: sub-folder-policy'

  def test_egress_sub_policy_deny_wrong_target_sa(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    r = net.firewall.check_connectivity_egress(
        src_ip=ipaddress.ip_network('10.102.0.1/32'),  #
        ip_protocol='tcp',
        port=2000,
        target_service_account='foobar@compute-system.iam.gserviceaccount.com')
    assert r.action == 'deny'

  def test_get_egress_rules(self):
    net = network.get_network(
        project_id=DUMMY_GCE_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_GCE_PROJECT_ID))
    pattern = re.compile(r'default-allow-.*')
    rules = net.firewall.get_vpc_egress_rules(name_pattern=pattern)
    assert 'default-allow-rdp' in [r.name for r in rules]
    assert 'default-allow-ssh' in [r.name for r in rules]

    rules = net.firewall.get_vpc_egress_rules(name='default-allow-ssh')
    assert 'default-allow-ssh' == rules[0].name
    assert 'tcp' == rules[0].allowed[0]['IPProtocol']
    assert '22' in rules[0].allowed[0]['ports']

    rules = net.firewall.get_vpc_egress_rules(name='not-existing-rule')
    assert 'default-allow-ssh' not in [r.name for r in rules]

  def test_get_addresses(self):
    """get addresses by project."""
    addresses = network.get_addresses(project_id=DUMMY_VPC_PROJECT_ID)
    assert len(addresses) > 2

    for address in addresses:
      if address.name == 'address1':
        assert address.short_path == 'gcpdiag-vpc1-aaaa/address1'

      if address.name == 'address2':
        assert address.short_path == 'gcpdiag-vpc1-aaaa/address2'

      if address.name == 'address3':
        assert address.short_path == 'gcpdiag-vpc1-aaaa/address3'

      if address.name == 'address4':
        assert address.short_path == 'gcpdiag-vpc1-aaaa/address4'

  def test_get_router_by_name(self):
    router = network.get_router_by_name(project_id='gcpdiag-gke1-aaaa',
                                        region='europe-west4',
                                        router_name='gke-default-router')
    assert router.name == 'gke-default-router'

    router = network.get_router_by_name(project_id='gcpdiag-gke1-aaaa',
                                        region='us-east4',
                                        router_name='dummy-router1')
    assert router.name == 'dummy-router1'

    router = network.get_router_by_name(project_id='gcpdiag-gke1-aaaa',
                                        region='us-east4',
                                        router_name='dummy-router2')
    assert router.name == 'dummy-router2'

    router = network.get_router_by_name(project_id='gcpdiag-gke1-aaaa',
                                        region='us-east4',
                                        router_name='dummy-router3')
    assert router.name == 'dummy-router3'

  def test_bgp_peer_status(self):
    vlan_router_status = network.nat_router_status('gcpdiag-interconnect1-aaaa',
                                                   router_name='dummy-router1',
                                                   region='us-east4')
    assert get_path(vlan_router_status.bgp_peer_status[0], ('state'),
                    default=None) == 'Established'
    assert get_path(vlan_router_status.bgp_peer_status[1], ('state'),
                    default=None) == 'Established'

    vlan_router_status = network.nat_router_status('gcpdiag-interconnect1-aaaa',
                                                   router_name='dummy-router2',
                                                   region='us-east4')
    assert get_path(vlan_router_status.bgp_peer_status[0], ('state'),
                    default=None) == 'Established'
    assert get_path(vlan_router_status.bgp_peer_status[1], ('state'),
                    default=None) == 'Idle'

  def test_firewall_policy_sorting_same_ip(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    # Check that deny rule is matched before allow rule with same priority and
    # same src ip range
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.104.0.1/32'),
        ip_protocol='tcp',
        port=80)
    assert r.action == 'deny'
    assert r.matched_by_str == (
        'policy: test-sorting-same-ip-policy, rule: deny rule with priority'
        ' 1000 and same src ip range')

  def test_firewall_policy_sorting(self):
    net = network.get_network(
        project_id=DUMMY_PROJECT_ID,
        network_name=DUMMY_DEFAULT_NETWORK,
        context=models.Context(project_id=DUMMY_PROJECT_ID))
    # Check that deny rule is matched before allow rule with same priority
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.104.0.1/32'),
        ip_protocol='tcp',
        port=80)
    assert r.action == 'deny'
    expected_matched_str = (
        'policy: test-sorting-same-ip-policy, rule: deny rule with priority'
        ' 1000 and same src ip range')
    assert r.matched_by_str == expected_matched_str

    # Check that allow rule with lower priority is matched before deny rule
    # with higher priority
    r = net.firewall.check_connectivity_ingress(
        src_ip=ipaddress.ip_network('10.101.0.1/32'),
        ip_protocol='tcp',
        port=2001)
    assert r.action == 'allow'
    assert r.matched_by_str == 'policy: parent-folder-policy'
