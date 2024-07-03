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
"""Queries related networkmanagement API."""

import ipaddress
import logging
import time
import uuid
from typing import Union

from gcpdiag import caching
from gcpdiag.queries import apis

IPv4AddrOrIPv6Addr = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
IPv4NetOrIPv6Net = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IPAddrOrNet = Union[IPv4AddrOrIPv6Addr, IPv4NetOrIPv6Net]


@caching.cached_api_call(in_memory=False)
def run_connectivity_test(project_id: str, src_ip: str, dest_ip: str,
                          dest_port: int, protocol: str):
  """Method to create/run an idempotent connectivity test"""
  test_id = f'gcpdiag-connectivity-test-{uuid.uuid4()}'
  # initialize the networkmanagement api
  networkmanagement = apis.get_api('networkmanagement', 'v1', project_id)

  # test input
  test_input = {
      'source': {
          'ipAddress': src_ip,
          'networkType': 'GCP_NETWORK'
      },
      'destination': {
          'ipAddress': dest_ip,
          'port': dest_port
      },
      'protocol': protocol
  }

  create_request = (networkmanagement.projects().locations().global_(
  ).connectivityTests().create(parent=f'projects/{project_id}/locations/global',
                               testId=test_id,
                               body=test_input)).execute()
  logging.info('Running a new connectivity test..')

  # Wait a max of 60 seconds to fetch the request_status.
  count = 0
  create_status = networkmanagement.projects().locations().global_().operations(
  ).get(name=create_request['name']).execute()
  while not create_status['done'] and count <= 15:
    time.sleep(4)
    create_status = networkmanagement.projects().locations().global_(
    ).operations().get(name=create_request['name']).execute()
    count += 1

  if create_status['done']:
    # get the result of the connectivity test
    res = (networkmanagement.projects().locations().global_().connectivityTests(
    ).get(
        name=
        f'projects/{project_id}/locations/global/connectivityTests/{test_id}'))
    result = res.execute()

    return result
  else:
    logging.warning('Timeout running the connectivity test...')
  return None
