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
from typing import Any, Dict, Iterable, List, Optional, Union

from gcpdiag import caching, config, models
from gcpdiag.queries import apis


class Network(models.Resource):
  """A VPC network."""
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
    return self._resource_data['selfLink']

  @property
  def firewall(self) -> 'EffectiveFirewalls':
    return _get_effective_firewalls(self)


IPAddrOrNet = Union[ipaddress.IPv4Address, ipaddress.IPv6Address,
                    ipaddress.IPv4Network, ipaddress.IPv6Network]


def _ip_match(
    ip1: IPAddrOrNet, ip2_list: List[Union[ipaddress.IPv4Network,
                                           ipaddress.IPv6Network]]) -> bool:
  """Match IP address or network to a network list (i.e. verify that ip1 is
  included in any ip of ip2_list)."""
  for ip2 in ip2_list:
    if isinstance(ip1, (ipaddress.IPv4Address, ipaddress.IPv6Address)):
      # ip1: address, ip2: network
      if ip1 in ip2:
        return True
    else:
      # ip1: network, ip2: network
      if isinstance(ip1, ipaddress.IPv4Network) and \
         isinstance(ip2, ipaddress.IPv4Network) and \
         ip1.subnet_of(ip2):
        return True
      elif isinstance(ip1, ipaddress.IPv6Network) and \
         isinstance(ip2, ipaddress.IPv6Network) and \
         ip1.subnet_of(ip2):
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


def _vpc_allow_deny_match(protocol: str, port: int,
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
      if protocol != l4_rule['IPProtocol']:
        continue
      if 'ports' not in l4_rule:
        return action
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


class _FirewallPolicy:
  """Represents a org/folder firewall policy."""

  @property
  def short_name(self):
    return self._resource_data['shortName']

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
        if 'dstIpRanges' in rule['match']:
          rule_decoded['match']['dstIpRanges'] = \
            [ipaddress.ip_network(net) for net in rule['match']['dstIpRanges']]
      self._rules[rule['direction']].append(rule_decoded)

  def check_connectivity_ingress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: int,
      #target_network: Optional[Network] = None, # useless unless targetResources set by API.
      target_service_account: Optional[str] = None
  ) -> FirewallCheckResult:
    for rule in self._rules['INGRESS']:
      if rule.get('disabled'):
        continue
      # src_ip
      if not _ip_match(src_ip, rule['match']['srcIpRanges']):
        continue
      # ip_protocol and port
      if not _l4_match(ip_protocol, port, rule['match']['layer4Configs']):
        continue
      # targetResources doesn't seem to get set. See also b/209450091.
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
      port: int,
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
      # disabled?
      if rule.get('disabled'):
        continue

      # source
      if 'sourceRanges' in rule and \
          _ip_match(src_ip, rule['sourceRanges']):
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

      # ip_protocol and port
      result = _vpc_allow_deny_match(ip_protocol,
                                     port,
                                     allowed=rule.get('allowed', []),
                                     denied=rule.get('denied', []))
      if result:
        logging.debug('vpc firewall: %s -> %s/%s = %s (%s)', src_ip, port,
                      ip_protocol, result, rule['name'])
        return FirewallCheckResult(result,
                                   vpc_firewall_rule_id=rule['id'],
                                   vpc_firewall_rule_name=rule['name'])
    # implied deny
    logging.debug('vpc firewall: %s -> %s/%s = %s (implied rule)', src_ip, port,
                  ip_protocol, 'deny')
    return FirewallCheckResult('deny')

  def get_ingress_rule_src_ips(self, name: str) -> List[Any]:
    """See documentation for EffectiveFirewalls.get_ingress_rule_src_ips()."""
    # Note: testing for this is done in gke_test.py
    for rule in self._rules['INGRESS']:
      if rule['name'] == name:
        if not rule['disabled']:
          return rule['sourceRanges']
        else:
          raise FirewallRuleNotFoundError(name, disabled=True)
    raise FirewallRuleNotFoundError(name)

  def verify_ingress_rule_exists(self, name: str):
    """See documentation for EffectiveFirewalls.verify_ingress_rule_exists()."""
    return any(r['name'] == name for r in self._rules['INGRESS'])


class EffectiveFirewalls:
  """Effective firewall rules for a VPC network.

  Includes org/folder firewall policies)."""
  _resource_data: dict
  _network: Network
  _policies: List[_FirewallPolicy]
  _vpc_firewall: _VpcFirewall

  def __init__(self, network, resource_data):
    self._network = network
    self._resource_data = resource_data
    self._policies = []
    if 'firewallPolicys' in resource_data:
      for policy in resource_data['firewallPolicys']:
        self._policies.append(_FirewallPolicy(policy))
    self._vpc_firewall = _VpcFirewall(resource_data['firewalls'])

  def check_connectivity_ingress(
      self,  #
      *,
      src_ip: IPAddrOrNet,
      ip_protocol: str,
      port: int,
      source_service_account: Optional[str] = None,
      source_tags: Optional[List[str]] = None,
      target_service_account: Optional[str] = None,
      target_tags: Optional[List[str]] = None) -> FirewallCheckResult:

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

  def get_ingress_rule_src_ips(self, name: str) -> List[Any]:
    """Retrieve the source IPs of a specific ingress firewall rule.

    This is specifically used to retrieve the list of GKE masters
    by reading the configuration of the automatically generated firewall
    rule that covers masters to node communication. See also: b/72535654

    Throws FirewallRuleNotFoundError if the rule is not found.
    """
    # Note that we chose for now not to provide full introspection for
    # firewall rules outside of this module (like: fw.get_firewalls()[0].name,
    # etc.), because at the moment the main use cases for rules should be
    # covered by check_connectivity_ingress() and we want to avoid the
    # complexity of creating a model for the whole firewall configuration.
    return self._vpc_firewall.get_ingress_rule_src_ips(name)

  def verify_ingress_rule_exists(self, name: str):
    """Verify that a certain VPC rule exists. This is useful to verify
    whether maybe a permission was missing on a shared VPC and an
    automatic rule couldn't be created."""
    return self._vpc_firewall.verify_ingress_rule_exists(name)


@caching.cached_api_call()
def _get_effective_firewalls(network: Network):
  compute = apis.get_api('compute', 'v1', network.project_id)
  request = compute.networks().getEffectiveFirewalls(project=network.project_id,
                                                     network=network.name)
  response = request.execute(num_retries=config.API_RETRIES)
  return EffectiveFirewalls(network, response)


@caching.cached_api_call()
def get_network(project_id: str, network_id: str):
  compute = apis.get_api('compute', 'v1', project_id)
  request = compute.networks().get(project=project_id, network=network_id)
  response = request.execute(num_retries=config.API_RETRIES)
  return Network(project_id, response)
