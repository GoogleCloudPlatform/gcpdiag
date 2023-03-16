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

DUMMY_PROJECT_ID = 'gcpdiag-interconnect1-aaaa'
DUMMY_INTERCONNECT = 'dummy-interconnect1'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestInterconnect:
  """Test Interconnect."""

  def test_get_interconnect(self):
    """get interconnect by name."""
    link = interconnect.get_interconnect(project_id=DUMMY_PROJECT_ID,
                                         interconnect_name=DUMMY_INTERCONNECT)
    assert link.name == DUMMY_INTERCONNECT
    assert len(link.attachments) == 2
