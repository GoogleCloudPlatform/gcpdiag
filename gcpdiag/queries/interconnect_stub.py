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
"""Stub API calls used in interconnect.py for testing.

Instead of doing real API calls, we return test JSON data.
"""

from gcpdiag.queries import apis_stub

# pylint: disable=unused-argument
# pylint: disable=invalid-name

DUMMY_INTERCONNECTS = 'compute-interconnects'
DUMMY_ATTACHMENTS = 'interconnect-attachments'


class InterconnectApiStub(apis_stub.ApiStub):
  """Mock object to simulate interconnect api calls.

  This object is created by GceApiStub, not used directly in test scripts."""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  # pylint: disable=redefined-builtin
  def get(self, project, interconnect):
    if self.mock_state == 'interconnects':
      interconnect_data = _find_test_data(interconnect)
      return apis_stub.RestCallStub(project, interconnect_data)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  # pylint: disable=redefined-builtin
  def list(self, project):
    if self.mock_state == 'interconnects':
      return apis_stub.RestCallStub(project, DUMMY_INTERCONNECTS)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')


def _find_test_data(interconnect_name):
  if interconnect_name.startswith('dummy-'):
    return interconnect_name.replace('dummy-', 'compute-')
  return interconnect_name


class VlanAttachmentApiStub(apis_stub.ApiStub):
  """Mock object to simulate interconnect attachment api calls.

  This object is created by GceApiStub, not used directly in test scripts."""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  # pylint: disable=redefined-builtin
  def get(self, project, region, interconnectAttachment):
    if self.mock_state == 'vlan_attachment':
      return apis_stub.RestCallStub(project, interconnectAttachment)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')

  # pylint: disable=redefined-builtin
  def aggregatedList(self, project):
    if self.mock_state == 'vlan_attachment':
      return apis_stub.RestCallStub(project, DUMMY_ATTACHMENTS)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')
