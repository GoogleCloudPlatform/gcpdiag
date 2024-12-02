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
DUMMY_PROJECT2_ID = 'gcpdiag-lb2-aaaa'
DUMMY_PROJECT3_ID = 'gcpdiag-lb3-aaaa'
DUMMY_PORT = 80
DUMMY_PROTOCOL = 'HTTP'
DUMMY_URLMAP_NAME = 'web-map-http'
DUMMY_TARGET_NAME = 'http-lb-proxy'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestURLMap:
  """Test lb.URLMap."""

  def test_get_backend_services(self):
    """get_backend_services returns the right backend services matched by name."""
    context = models.Context(project_id=DUMMY_PROJECT_ID)
    obj_list = lb.get_backend_services(context.project_id)
    assert len(obj_list) == 1
    n = obj_list[0]
    assert n.session_affinity == 'NONE'
    assert n.locality_lb_policy == 'ROUND_ROBIN'

  def test_get_backend_service_global(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    obj = lb.get_backend_service(context.project_id, 'web-backend-service')

    assert obj.name == 'web-backend-service'
    assert obj.session_affinity == 'NONE'
    assert obj.locality_lb_policy == 'ROUND_ROBIN'
    assert obj.protocol == 'HTTP'
    assert obj.load_balancer_type == lb.LoadBalancerType.CLASSIC_APPLICATION_LB

  def test_get_backend_service_regional(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    obj = lb.get_backend_service(context.project_id, 'backend-service-2',
                                 'europe-west4')

    assert obj.name == 'backend-service-2'
    assert obj.region == 'europe-west4'
    assert obj.session_affinity == 'NONE'
    assert obj.locality_lb_policy == 'ROUND_ROBIN'
    assert obj.protocol == 'TCP'
    assert obj.load_balancer_type == lb.LoadBalancerType.EXTERNAL_PASSTHROUGH_LB

  def test_get_backend_service_health_implicit_global(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    states_list = lb.get_backend_service_health(context.project_id,
                                                'web-backend-service')

    assert len(states_list) == 2
    assert states_list[0].health_state == 'UNHEALTHY'

  def test_get_backend_service_health_explicit_global(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    states_list = lb.get_backend_service_health(context.project_id,
                                                'web-backend-service', 'global')

    assert len(states_list) == 2
    assert states_list[0].health_state == 'UNHEALTHY'

  def test_get_backend_service_health_regional(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    states_list = lb.get_backend_service_health(context.project_id,
                                                'backend-service-2',
                                                'europe-west4')

    assert len(states_list) == 1
    assert states_list[0].health_state == 'UNHEALTHY'

  def test_get_forwarding_rules(self):
    """get_forwarding_rules returns the right forwarding rules matched by name."""
    forwarding_rules = lb.get_forwarding_rules(project_id=DUMMY_PROJECT_ID)
    assert len(forwarding_rules) == 1
    forwarding_rule = forwarding_rules[0]
    assert forwarding_rule.name == 'forwardingRule1'
    assert forwarding_rule.short_path == 'gcpdiag-lb1-aaaa/forwardingRule1'

  def test_get_forwarding_rule_regional(self):
    """get_forwarding_rule returns the right forwarding rule matched by name."""
    forwarding_rule = lb.get_forwarding_rule(
        project_id=DUMMY_PROJECT2_ID,
        forwarding_rule_name='forwardingRule1',
        region='us-west1',
    )
    assert forwarding_rule.name == 'forwardingRule1'
    assert forwarding_rule.short_path == 'gcpdiag-lb2-aaaa/forwardingRule1'
    assert (forwarding_rule.load_balancer_type ==
            lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB)

  def test_get_forwarding_rule_global(self):
    """get_forwarding_rule returns the right forwarding rule matched by name."""
    forwarding_rule = lb.get_forwarding_rule(
        project_id=DUMMY_PROJECT3_ID,
        forwarding_rule_name='https-content-rule',
    )
    assert forwarding_rule.name == 'https-content-rule'
    assert (forwarding_rule.load_balancer_type ==
            lb.LoadBalancerType.CLASSIC_APPLICATION_LB)

  def test_forwarding_rule_related_backend_service_http(self):
    forwarding_rule = lb.get_forwarding_rule(
        project_id=DUMMY_PROJECT3_ID, forwarding_rule_name='https-content-rule')

    related_backend_service = forwarding_rule.get_related_backend_services()

    assert len(related_backend_service) == 1
    assert related_backend_service[0].name == 'web-backend-service'

  def test_get_ssl_certificate_global(self):
    """get_ssl_certificate returns the right SSL certificate matched by name."""
    obj = lb.get_ssl_certificate(project_id=DUMMY_PROJECT3_ID,
                                 certificate_name='cert1')
    assert obj.name == 'cert1'
    assert obj.type == 'MANAGED'
    assert 'natka123.com' in obj.domains
    assert 'second.natka123.com' in obj.domains

  def test_get_target_https_proxies(self):
    """get_target_https_proxy returns the list of target https proxies."""
    items = lb.get_target_https_proxies(project_id=DUMMY_PROJECT3_ID)

    assert len(items) == 2
    assert items[0].name == 'https-lb-proxy'
    assert (
        items[0].full_path ==
        'projects/gcpdiag-lb3-aaaa/global/targetHttpsProxies/https-lb-proxy')
    assert items[1].name == 'https-lb-proxy-working'

  def test_get_target_ssl_proxies(self):
    """get_target_https_proxy returns the list of target ssl proxies."""
    items = lb.get_target_ssl_proxies(project_id=DUMMY_PROJECT3_ID)

    assert len(items) == 1
    assert items[0].name == 'ssl-proxy'
    assert (items[0].full_path ==
            'projects/gcpdiag-lb3-aaaa/global/targetSslProxies/ssl-proxy')

  def test_get_lb_insights_for_a_project(self):
    context = models.Context(project_id=DUMMY_PROJECT2_ID)
    lb_insights = lb.get_lb_insights_for_a_project(context.project_id)

    assert lb_insights[0].is_health_check_port_mismatch_insight
    assert lb_insights[1].is_firewall_rule_insight
