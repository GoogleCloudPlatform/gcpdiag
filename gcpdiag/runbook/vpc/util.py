# Copyright 2023 Google LLC
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
"""Helpful functions used in different parts of the VPC runbooks"""

import ipaddress
import re

from gcpdiag.queries import network


# check that nic is a vaild nic
def is_valid_nic(nic: str):
  pattern = r'^nic([0-7])$'
  return bool(re.match(pattern, nic))


# check if an external IP is associated to the nic
def is_external_ip_on_nic(interfaces: list, nic: str):
  interface = [int for int in interfaces if nic == int['name']]
  return 'natIP' in str(interface)


# get the project and network for the nic
def get_nic_info(interfaces: list, nic: str):
  nic_info = {}
  pattern = r'/projects/([^/]+)/global/networks/([^/]+)'

  interface = [int for int in interfaces if nic == int['name']]
  nic_network_url = interface[0]['network']

  match = re.search(pattern, nic_network_url)

  if match:
    nic_info['project'] = match.group(1)
    nic_info['network'] = match.group(2)
  else:
    raise ValueError('Could not get network, project info from the network URL')
  return nic_info


# get network from url
def get_network_from_url(url):
  pattern = r'/projects/([^/]+)/global/networks/([^/]+)'
  match = re.search(pattern, url)
  if match:
    return match.group(2)
  else:
    raise ValueError('Could not get network from the network URL')


# get the routes for the nic sorted in desc order of destRange prefix length
def get_selected_route_for_dest_ip(project, net, dest_ip):
  routes = network.get_routes(project)
  nic_routes = [
      route for route in routes if get_network_from_url(route.network) == net
  ]

  # routes with destRange that matches the dest_ip
  matching_routes = [
      route for route in nic_routes
      if dest_ip in ipaddress.IPv4Network(route.dest_range)
  ]

  # return None if there are no matching routes.
  if not matching_routes:
    return None
  # sort the matching routes based on the longest prefix, the longest prefix wins
  # based on GCP VPC selection https://cloud.google.com/vpc/docs/routes#routeselection
  sorted_routes = sorted(
      matching_routes,
      key=lambda r: ipaddress.IPv4Network(r.dest_range).prefixlen,
      reverse=True)

  return sorted_routes[0]
