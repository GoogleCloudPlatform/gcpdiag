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
"""Queries related to VPC Networks."""

import copy
import dataclasses
import ipaddress
import logging
import re
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Union

from gcpdiag import caching, config, models
from gcpdiag.queries import apis, apis_utils, iam

IPv4AddrOrIPv6Addr = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPv4NetOrIPv6Net = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IPAddrOrNet = Union[IPv4AddrOrIPv6Addr, IPv4NetOrIPv6Net]


class Subnetwork(models.Resource):
  """A VPC subnetwork."""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def self_link(self) -> str:
    return self._resource_data.get('selfLink', '')

  @property
  def ip_network(self) -> IPv4NetOrIPv6Net:
    return ipaddress.ip_network(self._resource_data['ipCidrRange'])

  @property
  def region(self) -> str:
    # https://www.googleapis.com/compute/v1/projects/gcpdiag-gke1-aaaa/regions/europe-west4
    m = re.match(
        r'https://www.googleapis.com/compute/v1/projects/([^/]+)/regions/([^/]+)',
        self._resource_data['region'])
    if not m:
      raise RuntimeError(
          f"can't parse region URL: {self._resource_data['region']}")
    return m.group(2)

  def is_private_ip_google_access(self) -> bool:
    return self._resource_data.get('privateIpGoogleAccess', False)

  @property
  def network(self):
    return self._resource_data['network']


class Route(models.Resource):
  """A VPC Route."""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def kind(self) -> str:
    return self._resource_data['kind']

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def network(self) -> str:
    return self._resource_data['network']

  @property
  def tags(self) -> List[str]:
    if 'tags' in self._resource_data:
      return self._resource_data['tags']
    return []

  @property
  def dest_range(self) -> str:
    return self._resource_data['destRange']

  @property
  def next_hop_gateway(self) -> Optional[str]:
    if 'nextHopGateway' in self._resource_data:
      return self._resource_data['nextHopGateway']
    return None

  @property
  def next_hop_vpn_tunnel(self) -> Optional[str]:
    return self._resource_data.get('nextHopVpnTunnel')

  @property
  def next_hop_hub(self) -> Optional[str]:
    return self._resource_data.get('nextHopHub')

  @property
  def priority(self) -> int:
    return self._resource_data['priority']

  def get_next_hop(self) -> Union[Dict[str, Any], Optional[str]]:
    hop_types = {
        'nextHopGateway': 'nextHopGateway',
        'nextHopVpnTunnel': 'nextHopVpnTunnel',
        'nextHopHub': 'nextHopHub',
        'nextHopInstance': 'nextHopInstance',
        'nextHopAddress': 'nextHopAddress',
        'nextHopPeering': 'nextHopPeering',
        'nextHopIlb': 'nextHopIlb',
        'nextHopNetwork': 'nextHopNetwork',
        'nextHopIp': 'nextHopIp'
    }

    for hop_type, value in hop_types.items():
      if self._resource_data.get(hop_type):
        return {'type': value, 'link': self._resource_data[hop_type]}
    return None

  def check_route_match(self, ip1: IPAddrOrNet, ip2: str) -> bool:
    ip2_list = [ipaddress.ip_network(ip2)]
    if _ip_match(ip1, ip2_list, 'allow'):
      return True
    return False


class ManagedZone(models.Resource):
  """
  Represent a DNS zone (public or private

  https://cloud.google.com/dns/docs/reference/v1beta2/managedZones
  """
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def cloud_logging_config(self) -> bool:
    return self._resource_data['cloudLoggingConfig'].get('enableLogging', False)

  @property
  def is_public(self) -> bool:
    return self._resource_data['visibility'] == 'public'

  @property
  def vpc_attached(self) -> bool:
    if 'privateVisibilityConfig' not in self._resource_data:
      self._resource_data['privateVisibilityConfig'] = {}

    return (self._resource_data['privateVisibilityConfig'].get(
        'networks', False) or
            self._resource_data['privateVisibilityConfig'].get(
                'gkeClusters', False))

  @property
  def dnssec_config_state(self) -> bool:
    if 'dnssecConfig' not in self._resource_data:
      self._resource_data['dnssecConfig'] = {}

    return self._resource_data['dnssecConfig'].get('state', False)

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://dns.googleapis.com/dns/v1beta2/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def self_link(self) -> str:
    return self._resource_data.get('selfLink', '')


class Router(models.Resource):
  """A VPC Router."""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._nats = None

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def self_link(self) -> str:
    return self._resource_data.get('selfLink', '')

  def subnet_has_nat(self, subnetwork):
    if not self._resource_data.get('nats', []):
      return False
    for n in self._resource_data.get('nats', []):
      if n['sourceSubnetworkIpRangesToNat'] == 'LIST_OF_SUBNETWORKS':
        # Cloud NAT configure for specific subnets
        if 'subnetworks' in n and subnetwork.self_link in [
            s['name'] for s in n['subnetworks']
        ]:
          return True
      else:
        # Cloud NAT configured for all subnets
        return True
    return False


@dataclasses.dataclass
class Peering:
  """VPC Peerings"""

  name: str
  url: str
  state: str
  exports_custom_routes: bool
  imports_custom_routes: bool
  auto_creates_routes: bool

  def __str__(self):
    return self.name


class Network(models.Resource):
  """A VPC network."""
  _resource_data: dict
  _subnetworks: Optional[Dict[str, Subnetwork]]

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._subnetworks = None

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def self_link(self) -> str:
    return self._resource_data.get('selfLink', '')

  @property
  def firewall(self) -> 'EffectiveFirewalls':
    return _get_effective_firewalls(self)

  @property
  def subnetworks(self) -> Dict[str, Subnetwork]:
    return _batch_get_subnetworks(
        self._project_id, frozenset(self._resource_data.get('subnetworks', [])))

  @property
  def peerings(self) -> List[Peering]:
    return [
        Peering(peer['name'], peer['network'], peer['state'],
                peer['exportCustomRoutes'], peer['importCustomRoutes'],
                peer['autoCreateRoutes'])
        for peer in self._resource_data.get('peerings', [])
    ]


def _ip_match(  #
    ip1: IPAddrOrNet,
    ip2_list: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]],
    match_type: str = 'allow') -> bool:
  """Match IP address or network to a network list (i.e. verify that ip1 is
  included in any ip of ip2_list).

  If match_type is 'allow', ip1 will match any ip in ip2_list if it is a subnet.
  If match_type is 'deny', ip1 will match any ip in ip2_list if they overlap
  (i.e. even if only part of ip1 is matched, it should still be considered a match)."""
  for ip2 in ip2_list:
    if isinstance(ip1, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
      # ip1: address, ip2: network
      if ip1 in ip2:
        return True
    else:
      # ip1: network, ip2: network
      if isinstance(ip1, ipaddress.IPv4Network) and \
          isinstance(ip2, ipaddress.IPv4Network):
        if match_type == 'allow' and ip1.subnet_of(ip2):
          return True
        elif match_type == 'deny' and ip1.overlaps(ip2):
          return True
        else:
          logging.debug('network no match %s of %s (%s matching)', ip1, ip2,
                        match_type)
      elif isinstance(ip1, ipaddress.IPv6Network) and \
          isinstance(ip2, ipaddress.IPv6Network):
        if match_type == 'allow' and ip1.subnet_of(ip2):
          return True
        elif match_type == 'deny' and ip1.overlaps(ip2):
          return True
  return False


def _l4_match(protocol: str, port: int, l4c_list: Iterable[Dict[str,
                                                                Any]]) -> bool:
  """Match protocol and port to layer4Configs structure:

         "layer4Configs": [
            {
              "ipProtocol": string,
              "ports": [
                string
              ]
            }
  """
  for l4c in l4c_list:
    if l4c['ipProtocol'] not in [protocol, 'all']:
      continue
    if 'ports' not in l4c:
      return True
    for p_range in l4c['ports']:
      if _port_in_port_range(port, p_range):
        return True
  return False


def _port_in_port_range(port: int, port_range: str):
  try:
    parts = [int(p) for p in port_range.split('-', 1)]
  except (TypeError, ValueError) as e:
    raise ValueError(
        f'invalid port numbers in range syntax: {port_range}') from e
  if len(parts) == 2:
    return parts[0] <= port <= parts[1]
  elif len(parts) == 1:
    return parts[0] == port


def _vpc_allow_deny_match(protocol: str, port: Optional[int],
                          allowed: Iterable[Dict[str, Any]],
                          denied: Iterable[Dict[str, Any]]) -> Optional[str]:
  """Match protocol and port to allowed denied structure (VPC firewalls):

      "allowed": [
        {
          "IPProtocol": string,
          "ports": [
            string
          ]
        }
      ],
      "denied": [
        {
          "IPProtocol": string,
          "ports": [
            string
          ]
        }
      ],
  """
  for action, l4_rules in [('allow', allowed), ('deny', denied)]:
    for l4_rule in l4_rules:
      if l4_rule['IPProtocol'] not in [protocol, 'all']:
        continue
      if 'ports' not in l4_rule:
        return action
      if port is not None:
        for p_range in l4_rule['ports']:
          if _port_in_port_range(port, p_range):
            return action
  return None


@dataclasses.dataclass
class FirewallCheckResult:
  """The result of a firewall connectivity check."""

  action: str
  firewall_policy_name: Optional[str] = None
  firewall_policy_rule_description: Optional[str] = None
  vpc_firewall_rule_id: Optional[str] = None
  vpc_firewall_rule_name: Optional[str] = None

  def __str__(self):
    return self.action

  @property
  def matched_by_str(self):
    if self.firewall_policy_name:
      if self.firewall_policy_rule_description:
        return f'policy: {self.firewall_policy_name}, rule: {self.firewall_policy_rule_description}'
      else:
        return f'policy: {self.firewall_policy_name}'
    elif self.vpc_firewall_rule_name:
      return f'vpc firewall rule: {self.vpc_firewall_rule_name}'


class FirewallRuleNotFoundError(Exception):
  rule_name: str

  def __init__(self, name, disabled=False):
    # Call the base class constructor with the parameters it needs
    super().__init__(f'firewall rule not found: {name}')
    self.rule_name = name
    self.disabled = disabled


class VpcFirewallRule:
  """Represents firewall rule"""

  def __init__(self, resource_data):
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def source_ranges(self) -> List[ipaddress.IPv4Network]:
    return self._resource_data['sourceRanges']

  @property
  def target_tags(self) -> set:
    return self._resource_data['targetTags']

  @property
  def allowed(self) -> List[dict]:
    return self._resource_data['allowed']

  def is_enabled(self) -> bool:
    return not self._resource_data['disabled']


class _FirewallPolicy:
  """Represents a org/folder firewall policy."""

  @property
  def short_name(self):
    if self._resource_data.get('shortName'):
      return self._resource_data.get('shortName')
    else:
      return self._resource_data.get('name')

  def __init__(self, resource_data):
    self._resource_data = resource_data
    self._rules = {
        'INGRESS': [],
        'EGRESS': [],
    }
    for rule in sorted(resource_data['rules'],
                       key=lambda r: int(r['priority'])):
      rule_decoded = copy.deepcopy(rule)
      if 'match' in rule:
        # decode network ranges
        if 'srcIpRanges' in rule['match']:
          rule_decoded['match']['srcIpRanges'] = \
            [ipaddress.ip_network(net) for net in rule['match']['srcIpRanges']]
        if 'destIpRanges' in rule['match']:
          rule_decoded['match']['destIpRanges'] = \
            [ipaddress.ip_network(net) for net in rule['match']['destIpRanges']]
      self._rules[rule['direction']].append(rule_decoded)

  def check_connectivity_ingress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int],
      #target_network: Optional[Network] = None, # useless unless targetResources set by API.
      target_service_account: Optional[str] = None
  ) -> FirewallCheckResult:
    for rule in self._rules['INGRESS']:
      if rule.get('disabled'):
        continue
      # To match networks, use 'supernet_of' for deny, because if the network that we
      # are checking is partially matched by a deny rule, it should still be considered
      # a match.
      ip_match_type = 'deny' if rule['action'] == 'deny' else 'allow'
      # src_ip
      if not _ip_match(src_ip, rule['match']['srcIpRanges'], ip_match_type):
        continue
      # ip_protocol and port
      if port is not None and not _l4_match(ip_protocol, port,
                                            rule['match']['layer4Configs']):
        continue
      # targetResources doesn't seem to get set. See also b/209450091.
      # please also check the check_connectivity_egress for similar issue.
      # if 'targetResources' in rule:
      #   if not target_network:
      #     continue
      #   if not any(
      #       tn == target_network.self_link for tn in rule['targetResources']):
      #     continue
      # target_service_account
      if 'targetServiceAccounts' in rule:
        if not target_service_account:
          continue
        if not any(sa == target_service_account
                   for sa in rule['targetServiceAccounts']):
          continue
      logging.debug('policy %s: %s -> %s/%s = %s', self.short_name, src_ip,
                    port, ip_protocol, rule['action'])
      return FirewallCheckResult(
          rule['action'],
          firewall_policy_name=self.short_name,
          firewall_policy_rule_description=rule['description'])

    # It should never happen that no rule match, because there should
    # be a low-priority 'goto_next' rule.
    logging.warning('unexpected no-match in firewall policy %s',
                    self.short_name)
    return FirewallCheckResult('goto_next')

  def check_connectivity_egress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int],
      #target_network: Optional[Network] = None, # useless unless targetResources set by API.
      target_service_account: Optional[str] = None
  ) -> FirewallCheckResult:
    for rule in self._rules['EGRESS']:
      # Do not evaluate disabled rules or automatically created rules
      if rule.get('disabled') or not rule.get('match', {}).get('destIpRanges'):
        continue
      # To match networks, use 'supernet_of' for deny, because if the network that we
      # are checking is partially matched by a deny rule, it should still be considered
      # a match.
      ip_match_type = 'deny' if rule['action'] == 'deny' else 'allow'
      # src_ip
      if not _ip_match(src_ip, rule['match']['destIpRanges'], ip_match_type):
        continue
      # ip_protocol and port
      if port is not None and not _l4_match(ip_protocol, port,
                                            rule['match']['layer4Configs']):
        continue
      # target_service_account
      if 'targetServiceAccounts' in rule:
        if not target_service_account:
          continue
        if not any(sa == target_service_account
                   for sa in rule['targetServiceAccounts']):
          continue
      logging.debug('policy %s: %s -> %s/%s = %s', self.short_name, src_ip,
                    port, ip_protocol, rule['action'])
      return FirewallCheckResult(
          rule['action'],
          firewall_policy_name=self.short_name,
          firewall_policy_rule_description=rule['description'])

    # It should never happen that no rule match, because there should
    # be a low-priority 'goto_next' rule.
    logging.debug('unexpected no-match in firewall policy %s', self.short_name)
    return FirewallCheckResult('goto_next')


class _VpcFirewall:
  """VPC Firewall Rules (internal class)"""
  _rules: dict

  def __init__(self, rules_list):
    self._rules = {
        'INGRESS': [],
        'EGRESS': [],
    }
    for r in sorted(rules_list, key=lambda r: int(r['priority'])):
      r_decoded = copy.deepcopy(r)
      # decode network ranges
      if 'sourceRanges' in r:
        r_decoded['sourceRanges'] = \
            [ipaddress.ip_network(net) for net in r['sourceRanges']]
      if 'destinationRanges' in r:
        r_decoded['destinationRanges'] = \
            [ipaddress.ip_network(net) for net in r['destinationRanges']]
      # use sets for tags
      if 'sourceTags' in r:
        r_decoded['sourceTags'] = set(r['sourceTags'])
      if 'targetTags' in r:
        r_decoded['targetTags'] = set(r['targetTags'])
      self._rules[r['direction']].append(r_decoded)

  def check_connectivity_ingress(
      self,
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int],
      # dest_ip: Optional[IPAddrOrNet] = None,
      source_service_account: Optional[str] = None,
      target_service_account: Optional[str] = None,
      source_tags: Optional[List[str]] = None,
      target_tags: Optional[List[str]] = None,
  ) -> FirewallCheckResult:
    if target_tags is not None and not isinstance(target_tags, list):
      raise ValueError('Internal error: target_tags must be a list')
    if source_tags is not None and not isinstance(source_tags, list):
      raise ValueError('Internal error: source_tags must be a list')

    for rule in self._rules['INGRESS']:
      #logging.debug('vpc firewall: %s -> %s/%s ? %s', src_ip, port, ip_protocol,
      #              rule['name'])

      # disabled?
      if rule.get('disabled'):
        continue

      # ip_protocol and port
      action = _vpc_allow_deny_match(ip_protocol,
                                     port,
                                     allowed=rule.get('allowed', []),
                                     denied=rule.get('denied', []))
      if not action:
        continue

      # source
      if 'sourceRanges' in rule and \
          _ip_match(src_ip, rule['sourceRanges'], action):
        pass
      elif source_service_account and \
          source_service_account in rule.get('sourceServiceAccounts', {}):
        pass
      elif source_tags and \
          set(source_tags) & rule.get('sourceTags', set()):
        pass
      else:
        continue

      # target
      if 'targetServiceAccounts' in rule:
        if not target_service_account:
          continue
        if not target_service_account in rule['targetServiceAccounts']:
          continue
      if 'targetTags' in rule:
        if not target_tags:
          continue
        if not set(target_tags) & rule['targetTags']:
          continue

      logging.debug('vpc firewall: %s -> %s/%s = %s (%s)', src_ip, port,
                    ip_protocol, action, rule['name'])
      return FirewallCheckResult(action,
                                 vpc_firewall_rule_id=rule['id'],
                                 vpc_firewall_rule_name=rule['name'])
    # implied deny
    logging.debug('vpc firewall: %s -> %s/%s = %s (implied rule)', src_ip, port,
                  ip_protocol, 'deny')
    return FirewallCheckResult('deny')

  def check_connectivity_egress(
      self,
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int],
      # dest_ip: Optional[IPAddrOrNet] = None,
      source_service_account: Optional[str] = None,
      target_service_account: Optional[str] = None,
      source_tags: Optional[List[str]] = None,
      target_tags: Optional[List[str]] = None,
  ) -> FirewallCheckResult:
    if target_tags is not None and not isinstance(target_tags, list):
      raise ValueError('Internal error: target_tags must be a list')
    if source_tags is not None and not isinstance(source_tags, list):
      raise ValueError('Internal error: source_tags must be a list')

    for rule in self._rules['EGRESS']:
      # disabled?
      if rule.get('disabled'):
        continue

      # ip_protocol and port
      action = _vpc_allow_deny_match(ip_protocol,
                                     port,
                                     allowed=rule.get('allowed', []),
                                     denied=rule.get('denied', []))
      if not action:
        continue

      # source
      if 'destinationRanges' in rule and \
          _ip_match(src_ip, rule['destinationRanges'], action):
        pass
      elif source_service_account and \
          source_service_account in rule.get('sourceServiceAccounts', {}):
        pass
      elif source_tags and \
          set(source_tags) & rule.get('sourceTags', set()):
        pass
      else:
        continue

      # target
      if 'targetServiceAccounts' in rule:
        if not target_service_account:
          continue
        if not target_service_account in rule['targetServiceAccounts']:
          continue
      if 'targetTags' in rule:
        if not target_tags:
          continue
        if not set(target_tags) & rule['targetTags']:
          continue

      logging.debug('vpc firewall: %s -> %s/%s = %s (%s)', src_ip, port,
                    ip_protocol, action, rule['name'])
      return FirewallCheckResult(action,
                                 vpc_firewall_rule_id=rule['id'],
                                 vpc_firewall_rule_name=rule['name'])
    # implied allow egress
    logging.debug('vpc firewall: %s -> %s/%s = %s (implied rule)', src_ip, port,
                  ip_protocol, 'allow')
    return FirewallCheckResult('allow')

  def verify_ingress_rule_exists(self, name: str):
    """See documentation for EffectiveFirewalls.verify_ingress_rule_exists()."""
    return any(r['name'] == name for r in self._rules['INGRESS'])

  def verify_egress_rule_exists(self, name: str):
    """See documentation for EffectiveFirewalls.verify_egress_rule_exists()."""
    return any(r['name'] == name for r in self._rules['EGRESS'])

  def get_vpc_ingress_rules(self,
                            name: Optional[str] = None,
                            name_pattern: Optional[Optional[re.Pattern]] = None,
                            target_tags: Optional[List[str]] = None):
    """See documentation for EffectiveFirewalls.get_vpc_ingress_rules()."""
    if not (name or name_pattern):
      raise ValueError('Internal error: name or name_pattern must be provided')
    if target_tags is not None and not isinstance(target_tags, list):
      raise ValueError('Internal error: target_tags must be a list')

    rules = []
    for rule in self._rules['INGRESS']:
      if name:
        if not rule['name'] == name:
          continue
      elif name_pattern:
        m = name_pattern.match(rule['name'])
        if not m:
          continue
      # filter by target_tags if needed
      if target_tags:
        if not 'targetTags' in rule:
          continue
        if not set(target_tags) & rule['targetTags']:
          continue
      rules.append(VpcFirewallRule(rule))

    return rules

  def get_vpc_egress_rules(self,
                           name: Optional[str] = None,
                           name_pattern: Optional[Optional[re.Pattern]] = None,
                           target_tags: Optional[List[str]] = None):
    """See documentation for EffectiveFirewalls.get_vpc_egress_rules()."""
    if not (name or name_pattern):
      raise ValueError('Internal error: name or name_pattern must be provided')
    if target_tags is not None and not isinstance(target_tags, list):
      raise ValueError('Internal error: target_tags must be a list')

    rules = []
    for rule in self._rules['EGRESS']:
      if name:
        if not rule['name'] == name:
          continue
      elif name_pattern:
        m = name_pattern.match(rule['name'])
        if not m:
          continue
      # filter by target_tags if needed
      if target_tags:
        if not 'targetTags' in rule:
          continue
        if not set(target_tags) & rule['targetTags']:
          continue

      rules.append(VpcFirewallRule(rule))
    return rules


class EffectiveFirewalls:
  """Effective firewall rules for a VPC network or Instance.

  Includes org/folder firewall policies)."""
  _resource_data: dict
  _policies: List[_FirewallPolicy]
  _vpc_firewall: _VpcFirewall

  def __init__(self, resource_data):
    self._resource_data = resource_data
    self._policies = []
    if 'firewallPolicys' in resource_data:
      for policy in resource_data['firewallPolicys']:
        self._policies.append(_FirewallPolicy(policy))
    self._vpc_firewall = _VpcFirewall(resource_data.get('firewalls', {}))

  def check_connectivity_ingress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int] = None,
      source_service_account: Optional[str] = None,
      source_tags: Optional[List[str]] = None,
      target_service_account: Optional[str] = None,
      target_tags: Optional[List[str]] = None) -> FirewallCheckResult:

    if ip_protocol != 'ICMP' and port is None:
      raise ValueError('TCP and UDP must have port numbers')

    # Firewall policies (organization, folders)
    for p in self._policies:
      result = p.check_connectivity_ingress(
          src_ip=src_ip,
          ip_protocol=ip_protocol,
          port=port,
          #target_network=self._network,
          target_service_account=target_service_account)
      if result.action != 'goto_next':
        return result

    # VPC firewall rules
    return self._vpc_firewall.check_connectivity_ingress(
        src_ip=src_ip,
        ip_protocol=ip_protocol,
        port=port,
        source_service_account=source_service_account,
        source_tags=source_tags,
        target_service_account=target_service_account,
        target_tags=target_tags)

  def check_connectivity_egress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: Optional[int] = None,
      source_service_account: Optional[str] = None,
      source_tags: Optional[List[str]] = None,
      target_service_account: Optional[str] = None,
      target_tags: Optional[List[str]] = None) -> FirewallCheckResult:

    if ip_protocol != 'ICMP' and port is None:
      raise ValueError('TCP and UDP must have port numbers')

    # Firewall policies (organization, folders)
    for p in self._policies:
      result = p.check_connectivity_egress(
          src_ip=src_ip,
          ip_protocol=ip_protocol,
          port=port,
          #target_network=self._network,
          target_service_account=target_service_account)
      if result.action != 'goto_next':
        return result

    # VPC firewall rules
    return self._vpc_firewall.check_connectivity_egress(
        src_ip=src_ip,
        ip_protocol=ip_protocol,
        port=port,
        source_service_account=source_service_account,
        source_tags=source_tags,
        target_service_account=target_service_account,
        target_tags=target_tags)

  def get_vpc_ingress_rules(
      self,
      name: Optional[str] = None,
      name_pattern: Optional[re.Pattern] = None,
      target_tags: Optional[List[str]] = None) -> List[VpcFirewallRule]:
    """Retrieve the list of ingress firewall rules matching name or name pattern and target tags.

    Args:
        name (Optional[str], optional): firewall rune name. Defaults to None.
        name_pattern (Optional[re.Pattern], optional): firewall rule name pattern. Defaults to None.
        target_tags (Optional[List[str]], optional): firewall target tags
          (if not specified any tag will match). Defaults to None.

    Returns:
        List[VpcFirewallRule]: List of ingress firewall rules
    """
    rules = self._vpc_firewall.get_vpc_ingress_rules(name, name_pattern,
                                                     target_tags)
    return rules

  def get_vpc_egress_rules(
      self,
      name: Optional[str] = None,
      name_pattern: Optional[re.Pattern] = None,
      target_tags: Optional[List[str]] = None) -> List[VpcFirewallRule]:
    """Retrieve the list of egress firewall rules matching name or name pattern and target tags.

    Args:
        name (Optional[str], optional): firewall rune name. Defaults to None.
        name_pattern (Optional[re.Pattern], optional): firewall rule name pattern. Defaults to None.
        target_tags (Optional[List[str]], optional): firewall target tags
          (if not specified any tag will match). Defaults to None.

    Returns:
        List[VpcFirewallRule]: List of egress firewall rules
    """
    rules = self._vpc_firewall.get_vpc_egress_rules(name, name_pattern,
                                                    target_tags)
    return rules

  def verify_ingress_rule_exists(self, name: str):
    """Verify that a certain VPC rule exists. This is useful to verify
    whether maybe a permission was missing on a shared VPC and an
    automatic rule couldn't be created."""
    return self._vpc_firewall.verify_ingress_rule_exists(name)

  def verify_egress_rule_exists(self, name: str):
    """Verify that a certain VPC rule exists. This is useful to verify
    whether maybe a permission was missing on a shared VPC and an
    automatic rule couldn't be created."""
    return self._vpc_firewall.verify_egress_rule_exists(name)


class VPCEffectiveFirewalls(EffectiveFirewalls):
  """Effective firewall rules for a VPC network.

  Includes org/folder firewall policies)."""
  _network: Network

  def __init__(self, network, resource_data):
    super().__init__(resource_data)
    self._network = network


@caching.cached_api_call()
def _get_effective_firewalls(network: Network):
  compute = apis.get_api('compute', 'v1', network.project_id)
  request = compute.networks().getEffectiveFirewalls(project=network.project_id,
                                                     network=network.name)
  response = request.execute(num_retries=config.API_RETRIES)
  return VPCEffectiveFirewalls(network, response)


@caching.cached_api_call(in_memory=True)
def get_network(project_id: str, network_name: str) -> Network:
  logging.info('fetching network: %s/%s', project_id, network_name)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.networks().get(project=project_id, network=network_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Network(project_id, response)


def get_subnetwork_from_url(url: str) -> Subnetwork:
  """Returns Subnetwork object given subnetwork url"""
  m = re.match((r'https://www.googleapis.com/compute/v1/projects/'
                r'([^/]+)/regions/([^/]+)/subnetworks/([^/]+)$'), url)
  if not m:
    raise ValueError(f"can't parse network url: {url}")
  (project_id, region, subnetwork_name) = (m.group(1), m.group(2), m.group(3))
  return get_subnetwork(project_id, region, subnetwork_name)


def get_network_from_url(url: str) -> Network:
  m = re.match(
      r'https://www.googleapis.com/compute/v1/projects/([^/]+)/global/networks/([^/]+)',
      url)
  if not m:
    raise ValueError(f"can't parse network url: {url}")
  (project_id, network_name) = (m.group(1), m.group(2))
  return get_network(project_id, network_name)


@caching.cached_api_call(in_memory=True)
def get_networks(project_id: str) -> List[Network]:
  logging.info('fetching network: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.networks().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [Network(project_id, item) for item in response.get('items', [])]


@caching.cached_api_call(in_memory=True)
def get_subnetwork(project_id: str, region: str,
                   subnetwork_name: str) -> Subnetwork:
  logging.info('fetching network: %s/%s', project_id, subnetwork_name)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.subnetworks().get(project=project_id,
                                      region=region,
                                      subnetwork=subnetwork_name)
  response = request.execute(num_retries=config.API_RETRIES)
  return Subnetwork(project_id, response)


@caching.cached_api_call(in_memory=True)
def _batch_get_subnetworks(
    project_id, subnetworks_urls: FrozenSet[str]) -> Dict[str, Subnetwork]:
  compute = apis.get_api('compute', 'v1', project_id)
  requests = []
  for subnet_url in subnetworks_urls:
    m = re.match((r'https://www.googleapis.com/compute/v1/projects/'
                  r'([^/]+)/regions/([^/]+)/subnetworks/([^/]+)$'), subnet_url)
    if not m:
      logging.warning("can't parse subnet URL: %s", subnet_url)
      continue
    requests.append(  #
        compute.subnetworks().get(project=m.group(1),
                                  region=m.group(2),
                                  subnetwork=m.group(3)))
  subnets = {}
  if not requests:
    return {}
  for (_, resp, exception) in apis_utils.batch_execute_all(compute, requests):
    if exception:
      logging.warning(exception)
      continue
    subnets[resp['selfLink']] = Subnetwork(project_id, resp)
  return subnets


@caching.cached_api_call(in_memory=True)
def get_routes(project_id: str) -> List[Route]:
  logging.info('fetching routes: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.routes().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return [Route(project_id, item) for item in response.get('items', [])]


@caching.cached_api_call(in_memory=True)
def get_zones(project_id: str) -> List[ManagedZone]:
  logging.info('fetching DNS zones: %s', project_id)
  dns = apis.get_api('dns', 'v1beta2', project_id)
  request = dns.managedZones().list(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  zones = []
  for zone in response.get('managedZones', []):
    request2 = dns.managedZones().get(project=project_id,
                                      managedZone=zone['name'])
    response2 = request2.execute(num_retries=config.API_RETRIES)
    zones.append(ManagedZone(project_id, response2))
  return zones


@caching.cached_api_call(in_memory=True)
def get_router(project_id: str, region: str, network) -> Router:
  logging.info('fetching routers: %s/%s', project_id, region)
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.routers().list(project=project_id,
                                   region=region,
                                   filter=f'network="{network.self_link}"')
  response = request.execute(num_retries=config.API_RETRIES)
  return Router(project_id, next(iter(response.get('items', [{}]))))


class VPCSubnetworkIAMPolicy(iam.BaseIAMPolicy):

  def _is_resource_permission(self, permission):
    return True


@caching.cached_api_call(in_memory=True)
def get_subnetwork_iam_policy(project_id: str, region: str,
                              subnetwork_name: str) -> VPCSubnetworkIAMPolicy:
  resource_name = (f'projects/{project_id}/regions/{region}/'
                   f'subnetworks/{subnetwork_name}')

  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.subnetworks().getIamPolicy(project=project_id,
                                               region=region,
                                               resource=subnetwork_name)

  return iam.fetch_iam_policy(request, VPCSubnetworkIAMPolicy, project_id,
                              resource_name)


class Address(models.Resource):
  """IP Addresses."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self.self_link)
    if result:
      return result.group(1)
    else:
      return f'>> {self.self_link}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def self_link(self) -> str:
    return self._resource_data.get('selfLink', '')

  @property
  def subnetwork(self) -> str:
    return self._resource_data['subnetwork']

  @property
  def status(self) -> str:
    return self._resource_data['status']


@caching.cached_api_call(in_memory=True)
def get_addresses(project_id: str) -> List[Address]:
  logging.info('fetching addresses list: %s', project_id)
  compute = apis.get_api('compute', 'v1', project_id)
  addresses = []
  request = compute.addresses().aggregatedList(project=project_id)
  response = request.execute(num_retries=config.API_RETRIES)
  addresses_by_regions = response['items']
  for _, data_ in addresses_by_regions.items():
    if 'addresses' not in data_:
      continue
    addresses.extend(
        [Address(project_id, address) for address in data_['addresses']])
  return addresses
