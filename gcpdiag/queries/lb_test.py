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
"""Test code in lb.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, lb

DUMMY_PROJECT_ID = 'gcpdiag-lb1-aaaa'
DUMMY_PROJECT_NAME = 'gcpdiag-lb1-aaaa'
DUMMY_PORT = 80
DUMMY_PROTOCOL = 'HTTP'
DUMMY_URLMAP_NAME = 'web-map-http'
DUMMY_TARGET_NAME = 'http-lb-proxy'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestURLMap:
  """Test lb.URLMap."""

  def test_get_backend_services(self):
    """get_backend_services returns the right backend services matched by name."""
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    obj_list = lb.get_backend_services(context.project_id)
    assert len(obj_list) == 1
    n = obj_list[0]
    assert n.session_affinity == 'NONE'
    assert n.locality_lb_policy == 'ROUND_ROBIN'
