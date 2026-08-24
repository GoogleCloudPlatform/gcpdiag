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
"""Test code in gke.py."""

import base64
import datetime
import ipaddress
import re
import unittest
from unittest import mock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from gcpdiag import models
from gcpdiag.queries import apis_stub, gce, gke
from gcpdiag.queries.gke import Version

DUMMY_PROJECT_NAME = 'gcpdiag-gke1-aaaa'
DUMMY_CLUSTER1_NAME = f'projects/{DUMMY_PROJECT_NAME}/zones/europe-west4-a/clusters/gke1'
DUMMY_CLUSTER1_LABELS = {'foo': 'bar'}
DUMMY_CLUSTER2_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west4/clusters/gke2'
DUMMY_CLUSTER2_SHORT_NAME = f'{DUMMY_PROJECT_NAME}/europe-west4/gke2'
DUMMY_CLUSTER1_SERVICE_ACCOUNT = '12340002-compute@developer.gserviceaccount.com'
DUMMY_CLUSTER2_SERVICE_ACCOUNT = 'gke2sa@gcpdiag-gke1-aaaa.iam.gserviceaccount.com'
DUMMY_CLUSTER3_NAME = f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west4/clusters/gke3'
DUMMY_CLUSTER4_NAME = f'projects/{DUMMY_PROJECT_NAME}/zones/europe-west4-a/clusters/gke4'
DUMMY_CLUSTER6_NAME = f'projects/{DUMMY_PROJECT_NAME}/zones/europe-west4-a/clusters/gke6'
DUMMY_AUTOPILOT_CLUSTER1_NAME = (
  f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west4/clusters/autopilot-gke1'
)
DUMMY_AUTOPILOT_CLUSTER2_NAME = (
  f'projects/{DUMMY_PROJECT_NAME}/locations/europe-west4/clusters/autopilot-gke2'
)
DUMMY_DEFAULT_NAME = 'default'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestCluster(unittest.TestCase):
  """Test gke.Cluster."""

  def test_get_clusters_by_label(self):
    """get_clusters returns the right cluster matched by label."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME, labels=DUMMY_CLUSTER1_LABELS)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters and len(clusters) == 1

  def test_get_clusters_by_region(self):
    """get_clusters returns the right cluster matched by region."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME, locations=['europe-west4'])
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters and len(clusters) == 7

  def test_get_clusters_by_region_gke5(self):
    """get_clusters returns the right cluster matched by region for gke5."""
    context = models.Context(project_id='gcpdiag-gke5-aaaa', locations=['europe-west4'])
    clusters = gke.get_clusters(context)
    expected_cluster_name = 'projects/gcpdiag-gke5-aaaa/zones/europe-west4-a/clusters/gke1'
    assert expected_cluster_name in clusters and len(clusters) == 9

  def test_cluster_properties(self):
    """verify cluster property methods."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.name == 'gke1'
    assert re.match(r'1\.\d+\.\d+-gke\.\d+', str(c.master_version))
    assert c.release_channel is None
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.name == 'gke4'
    assert c.release_channel == 'REGULAR'

  def test_get_path_regional(self):
    """full_path and short_path should return correct results with regional clusters."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.full_path == DUMMY_CLUSTER2_NAME
    assert str(c) == DUMMY_CLUSTER2_NAME
    assert c.short_path == DUMMY_CLUSTER2_SHORT_NAME

  def test_has_logging_enabled_false(self):
    """has_logging_enabled should return false for GKE cluster with logging disabled."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_logging_enabled()

  def test_has_logging_enabled_true(self):
    """has_logging_enabled should return true for GKE cluster with logging enabled."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.has_logging_enabled()

  def test_has_monitoring_enabled_false(self):
    """has_monitoring_enabled should return false for GKE cluster with monitoring disabled."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER1_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_monitoring_enabled()

  def test_has_monitoring_enabled_true(self):
    """has_monitoring_enabled should return true for GKE cluster with monitoring enabled."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER2_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.has_monitoring_enabled()

  def test_has_authenticator_group_enabled(self):
    """ ""has_authenticator_group_enabled should return true for GKE cluster with Groups for RBAC

    enabled.
    """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    assert DUMMY_CLUSTER3_NAME in clusters.keys()
    assert DUMMY_CLUSTER4_NAME in clusters.keys()
    c = clusters[DUMMY_CLUSTER3_NAME]
    assert c.has_authenticator_group_enabled()
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert not c.has_authenticator_group_enabled()

  def test_cluster_has_workload_identity_enabled(self):
    """has_workload_identity_enabled should return true for GKE cluster with

    workload identity enabled.
    """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_workload_identity_enabled()
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.has_workload_identity_enabled()

  def test_has_http_load_balancing_enabled(self):
    """has_http_load_balancing_enabled should return true if the GKE cluster has

    http load balancing enabled
    """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_http_load_balancing_enabled()
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.has_http_load_balancing_enabled()

  def test_has_default_service_account(self):
    """has_default_service_account should return true for GKE node-pools with

    the default GCE SA.
    """
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    # 'default-pool' has the default SA
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.nodepools[0].has_default_service_account()
    # 'default-pool' doesn't have the default SA
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert not c.nodepools[0].has_default_service_account()

  def test_pod_ipv4_cidr(self):
    """returns correct pod CIDR"""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.pod_ipv4_cidr.compare_networks(ipaddress.ip_network('192.168.1.0/24')) == 0
    # cluster 2
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.pod_ipv4_cidr.compare_networks(ipaddress.ip_network('10.4.0.0/14')) == 0

  def test_current_node_count(self):
    """returns correct number of nodes running"""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.current_node_count == 1
    # cluster 2
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.current_node_count == 3

  def test_np_pod_ipv4_cidr_size(self):
    """return correct pod CIDR size per allocated to node pool."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    # cluster 1
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.nodepools[0].pod_ipv4_cidr_size == 24

  def test_np_pod_ipv4_cidr_block(self):
    """Get the pod cidr range in use by the nodepool."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)

    # cluster 1 is vpc-native and has a value set for the nodepool cidr block
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert (
      c.nodepools[0].pod_ipv4_cidr_block.compare_networks(ipaddress.ip_network('192.168.1.0/24'))
      == 0
    )

    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.nodepools[0].pod_ipv4_cidr_block is None

  def test_has_md_concealment_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.nodepools[0].has_md_concealment_enabled()

  def test_has_workload_identity_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.nodepools[0].has_workload_identity_enabled()

  def test_has_intra_node_visibility_enabled(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER3_NAME]
    assert not c.has_intra_node_visibility_enabled()
    # Abusing an Autopilot cluster here as I cannot recreate the testfiles at the moment
    c = clusters[DUMMY_AUTOPILOT_CLUSTER1_NAME]
    assert c.has_intra_node_visibility_enabled()

  def test_no_accelerators(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.nodepools[0].config.has_accelerators()

  def test_has_accelerators(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER6_NAME]
    assert c.nodepools[0].config.has_accelerators()

  def test_no_maintenance_window(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_maintenance_window()

  def test_maintenance_window(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER6_NAME]
    assert c.has_maintenance_window()

  def test_nodepool_instance_groups(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    migs = c.nodepools[0].instance_groups
    assert len(migs) == 1
    m = next(iter(migs))
    assert m.is_gke()

  def test_get_node_by_instance_id(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    migs = c.nodepools[0].instance_groups
    assert len(migs) == 1
    m = next(iter(migs))
    found_nodes = 0
    for i in gce.get_instances(context).values():
      if m.is_instance_member(m.project_id, m.region, i.name):
        node = gke.get_node_by_instance_id(context, i.id)
        assert node.mig == m
        found_nodes += 1
    assert found_nodes == 1

  def test_service_account_property(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    # 'default-pool' has the default SA
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.nodepools[0].service_account == DUMMY_CLUSTER1_SERVICE_ACCOUNT
    # cluster2 has a custom SA
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.nodepools[0].service_account == DUMMY_CLUSTER2_SERVICE_ACCOUNT

  def test_masters_cidr_list(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.masters_cidr_list == [ipaddress.IPv4Network('10.0.1.0/28')]

  def test_cluster_is_private(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.is_private
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.is_private

  def test_cluster_is_vpc_native(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER3_NAME]
    assert not c.is_vpc_native
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.is_vpc_native

  def test_cluster_is_regional(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert not c.is_regional
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert c.is_regional

  def test_cluster_ca_certificate(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.cluster_ca_certificate == 'REDACTED'

  def test_cluster_endpoint(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert c.endpoint == '192.168.1.1'

  def test_node_tag_property(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert [t for t in c.nodepools[0].node_tags if t.startswith('gke-gke1-')]

    c = clusters[DUMMY_CLUSTER4_NAME]
    assert [t for t in c.nodepools[0].node_tags if t.endswith('-node')]

  def test_cluster_hash_property(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert re.match('[a-z0-9]+$', c.cluster_hash)

  def test_verify_firewall_rule_exists(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert c.network.firewall.verify_ingress_rule_exists(f'gke-gke4-{c.cluster_hash}-master')
    assert not c.network.firewall.verify_ingress_rule_exists('foobar')

  def test_cluster_network_subnetwork(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER4_NAME]
    assert DUMMY_DEFAULT_NAME == c.network.name
    assert DUMMY_DEFAULT_NAME == c.subnetwork.name
    assert c.subnetwork.ip_network == ipaddress.IPv4Network('10.164.0.0/20')

  def test_cluster_masters_cidr_list(self):
    # test both public and private clusters, because the code is quite
    # different for each of them.
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_AUTOPILOT_CLUSTER1_NAME]
    ips = c.masters_cidr_list
    assert len(ips) == 3
    assert isinstance(ips[0], ipaddress.IPv4Network)
    assert not ips[0].is_private
    c = clusters[DUMMY_CLUSTER4_NAME]
    ips = c.masters_cidr_list
    assert len(ips) == 1
    assert isinstance(ips[0], ipaddress.IPv4Network)
    assert ips[0].is_private

  def test_has_network_policy_enabled(self):
    # test for network policy enabled and disabled
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER1_NAME]
    assert not c.has_network_policy_enabled()

  def test_has_dpv2_enabled(self):
    # test for dpv2 enabled
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)
    c = clusters[DUMMY_CLUSTER2_NAME]
    assert not c.has_dpv2_enabled()
    c2 = clusters[DUMMY_AUTOPILOT_CLUSTER1_NAME]
    assert c2.has_dpv2_enabled()

  def test_is_nodelocal_dnscache_enabled(self):
    """Test the is_nodelocal_dnscache_enabled property."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)

    c1 = clusters[DUMMY_CLUSTER1_NAME]
    assert c1.is_nodelocal_dnscache_enabled

    c2 = clusters[DUMMY_CLUSTER2_NAME]
    assert not c2.is_nodelocal_dnscache_enabled

    c_autopilot = clusters[DUMMY_AUTOPILOT_CLUSTER1_NAME]
    assert c_autopilot.is_nodelocal_dnscache_enabled

  def test_dns_provider(self):
    """Test the dns_provider property."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    clusters = gke.get_clusters(context)

    c1 = clusters[DUMMY_CLUSTER1_NAME]
    assert c1.dns_provider == 'KUBE_DNS'

    c_autopilot = clusters[DUMMY_AUTOPILOT_CLUSTER1_NAME]
    assert c_autopilot.dns_provider == 'CLOUD_DNS'

    c_autopilot2 = clusters[DUMMY_AUTOPILOT_CLUSTER2_NAME]
    assert c_autopilot2.dns_provider == 'KUBE_DNS'


class TestVersion:
  """Test GKE Version class"""

  def test_init(self):
    Version('1.19.13-gke.701')
    self.raises('x.19.13-gke.701')
    self.raises('.19.13-gke.701')
    self.raises('1.x.13-gke.701')
    self.raises('1..13-gke.701')
    self.raises('x')

  def test_same_major(self):
    assert Version('1.19.13-gke.701').same_major(Version('1.23.45-six.7'))
    assert not Version('1.19.13-gke.701').same_major(Version('9.23.45-six.7'))

  def test_diff_minor(self):
    assert Version('1.19.13-gke.701').diff_minor(Version('1.23.45-six.7')) == 4
    assert Version('1.19.13-gke.701').diff_minor(Version('1.19.45-six.7')) == 0

  def test_eq_str(self):
    assert Version('1.19.13-gke.701') == '1.19.13-gke.701'
    assert Version('1.19.13-gke.701') != '1.19.13-gke.702'

  def test_add_str(self):
    assert 'the version is: ' + Version('1.19.13-gke.701') == 'the version is: 1.19.13-gke.701'
    assert Version('1.19.13-gke.701') + '!' == '1.19.13-gke.701!'
    with pytest.raises(TypeError):
      assert Version('1.19.13-gke.701') + 42
    with pytest.raises(TypeError):
      assert 42 + Version('1.19.13-gke.701')
    with pytest.raises(TypeError):
      assert Version('1.19.13-gke.701') + Version('1.19.13-gke.701')

  def test_eq_version(self):
    assert Version('1.19.13-gke.701') == Version('1.19.13-gke.701')
    assert Version('1.19.13-gke.701') != Version('1.19.13-gke.702')

  def test_compare_lt_gt(self):
    assert Version('1.19.13-gke.701') < Version('2.19.13-gke.701')
    assert Version('1.19.13-gke.701') < Version('1.20.13-gke.701')
    assert Version('1.19.13-gke.701') < Version('1.19.14-gke.701')

    assert Version('1.19') < Version('1.19.13-gke.701')
    assert Version('1.19.13-gke.701') < Version('1.20')
    assert Version('1') < Version('1.19.13-gke.701')
    assert Version('1.19.13-gke.701') < Version('2')
    assert Version('1') < Version('2')

  def raises(self, v):
    with pytest.raises(Exception):
      Version(v)


def _generate_mock_cert(valid_days, expired=False):
  private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
  subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Mock CA')])
  now = datetime.datetime.now(datetime.timezone.utc)
  if expired:
    not_before = now - datetime.timedelta(days=valid_days + 10)
    not_after = now - datetime.timedelta(days=10)
  else:
    not_before = now - datetime.timedelta(days=10)
    not_after = now + datetime.timedelta(days=valid_days)

  cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(not_before)
    .not_valid_after(not_after)
    .sign(private_key, hashes.SHA256())
  )

  return cert.public_bytes(serialization.Encoding.PEM).decode('utf-8')


class TestClusterCaCertificateInfo:
  """Test parsing helper function under various certificate payload formats."""

  def test_parse_single_healthy_cert(self):
    pem = _generate_mock_cert(valid_days=300)
    b64_pem = base64.b64encode(pem.encode('utf-8')).decode('utf-8')
    context = models.Context(project_id='project-id')
    c = gke.Cluster(
      'project-id',
      {
        'currentMasterVersion': '1.20.0',
        'location': 'us-central1-a',
        'name': 'dummy-cluster',
        'masterAuth': {'clusterCaCertificate': b64_pem},
      },
      context,
    )
    cert_info = c.cluster_ca_certificate_info
    assert cert_info is not None
    assert len(cert_info['certificates']) == 1
    expiry = datetime.datetime.fromisoformat(cert_info['certificates'][0]['notAfter'])
    assert expiry > datetime.datetime.now(datetime.timezone.utc)

  def test_parse_multiple_certs_bundle(self):
    pem1 = _generate_mock_cert(valid_days=15)
    pem2 = _generate_mock_cert(valid_days=300)
    bundle = pem1 + pem2
    b64_bundle = base64.b64encode(bundle.encode('utf-8')).decode('utf-8')
    context = models.Context(project_id='project-id')
    c = gke.Cluster(
      'project-id',
      {
        'currentMasterVersion': '1.20.0',
        'location': 'us-central1-a',
        'name': 'dummy-cluster',
        'masterAuth': {'clusterCaCertificate': b64_bundle},
      },
      context,
    )
    cert_info = c.cluster_ca_certificate_info
    assert cert_info is not None
    assert len(cert_info['certificates']) == 2
    expiries = sorted(
      datetime.datetime.fromisoformat(c['notAfter']) for c in cert_info['certificates']
    )
    assert (expiries[0] - datetime.datetime.now(datetime.timezone.utc)).days < 20
    assert (expiries[1] - datetime.datetime.now(datetime.timezone.utc)).days > 290

  def test_parse_invalid_cert_fails(self):
    context = models.Context(project_id='project-id')
    c = gke.Cluster(
      'project-id',
      {
        'currentMasterVersion': '1.20.0',
        'location': 'us-central1-a',
        'name': 'dummy-cluster',
        'masterAuth': {'clusterCaCertificate': 'NOT_A_VALID_CERTIFICATE_PAYLOAD'},
      },
      context,
    )
    assert c.cluster_ca_certificate_info is None

  def test_parse_raw_pem_unencoded(self):
    pem = _generate_mock_cert(valid_days=300)
    context = models.Context(project_id='project-id')
    c = gke.Cluster(
      'project-id',
      {
        'currentMasterVersion': '1.20.0',
        'location': 'us-central1-a',
        'name': 'dummy-cluster',
        'masterAuth': {'clusterCaCertificate': pem},
      },
      context,
    )
    cert_info = c.cluster_ca_certificate_info
    assert cert_info is not None
    assert len(cert_info['certificates']) == 1
