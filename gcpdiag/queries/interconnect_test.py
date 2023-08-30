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
"""Test code in interconnect.py."""

from unittest import mock

# from gcpdiag import models
from gcpdiag.queries import apis_stub, interconnect

DUMMY_PROJECT_ID = 'gcpdiag-gke1-aaaa'
DUMMY_INTERCONNECT = 'dummy-interconnect1'
DUMMY_ATTACHMENT = 'dummy-attachment1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestInterconnect:
  """Test Interconnect."""

  def test_get_interconnect(self):
    """get interconnect by name."""
    link = interconnect.get_interconnect(project_id=DUMMY_PROJECT_ID,
                                         interconnect_name=DUMMY_INTERCONNECT)
    assert link.name == DUMMY_INTERCONNECT
    assert len(link.attachments) == 2
    assert link.metro == 'bos'

  def test_get_interconnects(self):
    """get interconnects by project."""
    links = interconnect.get_interconnects(project_id=DUMMY_PROJECT_ID)
    for link in links:
      if link.name == DUMMY_INTERCONNECT:
        assert 'dummy-attachment1' in link.attachments
        assert 'dummy-attachment2' in link.attachments
        assert link.ead == 'bos-zone1-219'

      if link.name == 'dummy-interconnect2':
        assert 'dummy-attachment3' in link.attachments
        assert 'dummy-attachment4' in link.attachments
        assert link.ead == 'bos-zone2-219'

      if link.name == 'dummy-interconnect3':
        assert 'dummy-attachment5' in link.attachments
        assert link.ead == 'sjc-zone1-6'

      if link.name == 'dummy-interconnect4':
        assert 'dummy-attachment6' in link.attachments
        assert link.ead == 'sjc-zone2-6'

  def test_get_vlan_attachment(self):
    """get interconnect by name."""
    attachment = interconnect.get_vlan_attachment(
        project_id=DUMMY_PROJECT_ID,
        region='us-east4',
        vlan_attachment='interconnect-attachment1')
    assert attachment.name == DUMMY_ATTACHMENT
    assert attachment.interconnect == DUMMY_INTERCONNECT
    assert attachment.metro in ['bos', 'sjc']
    assert attachment.region in ['us-east4', 'us-west2']

  def test_get_vlan_attachments(self):
    """get interconnects by project."""
    attachments = interconnect.get_vlan_attachments(project_id=DUMMY_PROJECT_ID)
    assert len(attachments) > 2

    for attachment in attachments:
      if attachment.name == 'dummy-attachment1':
        assert attachment.interconnect == 'dummy-interconnect1'
        assert attachment.ead == 'bos-zone1-219'
        assert attachment.router == 'dummy-router1'

      if attachment.name == 'dummy-attachment2':
        assert attachment.interconnect == 'dummy-interconnect1'
        assert attachment.ead == 'bos-zone1-219'
        assert attachment.router == 'dummy-router1'

      if attachment.name == 'dummy-attachment3':
        assert attachment.interconnect == 'dummy-interconnect2'
        assert attachment.ead == 'bos-zone2-219'
        assert attachment.router == 'dummy-router2'

      if attachment.name == 'dummy-attachment4':
        assert attachment.interconnect == 'dummy-interconnect2'
        assert attachment.ead == 'bos-zone2-219'
        assert attachment.router == 'dummy-router2'

      if attachment.name == 'dummy-attachment5':
        assert attachment.interconnect == 'dummy-interconnect3'
        assert attachment.ead == 'sjc-zone1-6'
        assert attachment.router == 'dummy-router3'

      if attachment.name == 'dummy-attachment6':
        assert attachment.interconnect == 'dummy-interconnect4'
        assert attachment.ead == 'sjc-zone2-6'
        assert attachment.router == 'dummy-router3'

  def test_legacy_dataplane(self):
    attachments = interconnect.get_vlan_attachments(project_id=DUMMY_PROJECT_ID)
    for attachment in attachments:
      if attachment.name == 'dummy-attachment7':
        assert attachment.legacy_dataplane is True
      if attachment.name == 'dummy-attachment8':
        assert attachment.legacy_dataplane is False
