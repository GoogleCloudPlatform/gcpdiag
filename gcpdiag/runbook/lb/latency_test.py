# Copyright 2024 Google LLC
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
"""Test class for lb/latency."""

import unittest
from unittest import mock

import apiclient

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.queries import lb as queries_lb
from gcpdiag.runbook import lb, op, snapshot_test_base
from gcpdiag.runbook.lb import flags
from gcpdiag.runbook.lb.latency import (LatencyEnd, LbBackendLatencyCheck,
                                        LbErrorRateCheck, LbLatencyStart,
                                        LbRequestCountCheck)


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = lb
  runbook_name = 'lb/latency'
  project_id = ''
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule',
      'region': 'global'
  }, {
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule-working',
      'region': 'global'
  }, {
      'project_id': 'gcpdiag-lb3-aaaa',
      'forwarding_rule_name': 'https-content-rule',
      'region': 'global',
      'backend_latency_threshold': '700000',
      'request_count_threshold': '700000',
      'error_rate_threshold': '50'
  }]


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestLatencyLogic(unittest.TestCase):
  """Unit tests for specific logic branches in latency.py."""

  def setUp(self):
    super().setUp()
    self.mock_fr = mock.MagicMock()
    self.mock_fr.name = 'test-fr'
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.GLOBAL_EXTERNAL_APPLICATION_LB)
    self.operator = op.Operator(mock.MagicMock())
    self.operator.parameters = {
        flags.PROJECT_ID: 'gcpdiag-lb3-aaaa',
        flags.FORWARDING_RULE_NAME: 'test-fr',
        flags.REGION: 'global',
        'start_time': '2024-01-01T00:00:00Z',
        'end_time': '2024-01-01T01:00:00Z',
        flags.BACKEND_LATENCY_THRESHOLD: 200,
        flags.REQUEST_COUNT_THRESHOLD: 150,
        flags.ERROR_RATE_THRESHOLD: 1,
    }
    self.operator.set_run_id('test')
    self.operator.set_step(mock.Mock(execution_id='test-step'))
    self.operator.messages = mock.MagicMock()

  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_unspecified_type(self, mock_skip, mock_get_fr):
    """Covers LbLatencyStart with unspecified LB type."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.LOAD_BALANCER_TYPE_UNSPECIFIED)
    mock_get_fr.return_value = self.mock_fr
    step = LbLatencyStart()

    with op.operator_context(self.operator):
      step.execute()

    mock_skip.assert_called_once_with(mock.ANY, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_unsupported_type(self, mock_skip, mock_get_fr):
    """Covers LbLatencyStart with unsupported LB type."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.EXTERNAL_PASSTHROUGH_LB)
    mock_get_fr.return_value = self.mock_fr
    step = LbLatencyStart()

    with op.operator_context(self.operator):
      step.execute()

    mock_skip.assert_called_once_with(mock.ANY, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_backend_latency_exception(self, mock_info, mock_get_fr, mock_query):
    """Covers exception handling in LbBackendLatencyCheck."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.side_effect = RuntimeError('Monitoring Error')
    step = LbBackendLatencyCheck()

    with op.operator_context(self.operator):
      with self.assertRaises(RuntimeError):
        step.execute()

    mock_info.assert_any_call(mock.ANY)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_backend_latency_empty_values(self, mock_get_fr, mock_query):
    """Covers fallback to [[0]] values in LbBackendLatencyCheck."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'other': 'data'}}
    step = LbBackendLatencyCheck()

    with op.operator_context(self.operator):
      step.execute()
      self.operator.interface.add_ok.assert_called_once()

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_backend_latency_regional_external(self, mock_get_fr, mock_query):
    """Covers Regional External LB branch in LbBackendLatencyCheck."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[100]]}}
    step = LbBackendLatencyCheck()

    with op.operator_context(self.operator):
      step.execute()

    query_str = mock_query.call_args[0][1]
    self.assertIn('http_external_regional_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_backend_latency_regional_internal(self, mock_get_fr, mock_query):
    """Covers  Regional Internal LB branch in LbBackendLatencyCheck."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[100]]}}
    step = LbBackendLatencyCheck()

    with op.operator_context(self.operator):
      step.execute()

    query_str = mock_query.call_args[0][1]
    self.assertIn('internal_http_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_request_count_regional_external(self, mock_get_fr, mock_query):
    """Covers Regional External LB branch in LbRequestCountCheck."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[10]]}}
    step = LbRequestCountCheck()

    with op.operator_context(self.operator):
      step.execute()

    query_str = mock_query.call_args[0][1]
    self.assertIn('http_external_regional_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_request_count_regional_internal(self, mock_get_fr, mock_query):
    """Covers Regional Internal LB branch in LbRequestCountCheck."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[10]]}}
    step = LbRequestCountCheck()

    with op.operator_context(self.operator):
      step.execute()

    query_str = mock_query.call_args[0][1]
    self.assertIn('internal_http_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_error_rate_calculation_and_regional_internal(self, mock_get_fr,
                                                        mock_query):
    """Covers Error rate calculation for Regional Internal."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_INTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[5]]}}
    step = LbErrorRateCheck(average_request_count=100)

    with op.operator_context(self.operator):
      step.execute()

    query_str = mock_query.call_args[0][1]
    self.assertIn('internal_http_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.config.get', return_value=False)
  @mock.patch('gcpdiag.runbook.op.prompt', return_value=op.YES)
  @mock.patch('gcpdiag.runbook.op.info')
  def test_latency_end_yes(self, mock_info, unused_mock_prompt,
                           unused_mock_config):
    """Covers LatencyEnd step logic."""
    step = LatencyEnd()

    with op.operator_context(self.operator):
      step.execute()

    mock_info.assert_called_with(message=op.END_MESSAGE)

  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=False)
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_compute_disabled(self, mock_skip, unused_mock_is_enabled):
    """Covers  Early exit when Compute API is disabled."""
    step = LbLatencyStart()
    with op.operator_context(self.operator):
      step.execute()
    mock_skip.assert_called_once_with(mock.ANY,
                                      reason='Compute API is not enabled')

  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_http_error(self, mock_skip, mock_get_fr):
    """Covers HttpError when fetching forwarding rule."""
    mock_get_fr.side_effect = apiclient.errors.HttpError(
        mock.Mock(status=404), b'Not Found')
    step = LbLatencyStart()
    with op.operator_context(self.operator):
      step.execute()
    mock_skip.assert_called_once_with(mock.ANY, reason=mock.ANY)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_request_count_exception(self, mock_info, mock_get_fr, mock_query):
    """Covers Exception handling in LbRequestCountCheck."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.side_effect = RuntimeError('Monitoring Error')
    step = LbRequestCountCheck()
    with op.operator_context(self.operator):
      with self.assertRaises(RuntimeError):
        step.execute()
    mock_info.assert_any_call(mock.ANY)

  def test_get_average_request_count(self):
    """Covers  get_average_request_count getter."""
    step = LbRequestCountCheck(average_request_count=12.5)
    self.assertEqual(step.get_average_request_count(), 12.5)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_error_rate_regional_external(self, mock_get_fr, mock_query):
    """Covers  Regional External LB branch in LbErrorRateCheck."""
    self.mock_fr.load_balancer_type = (
        queries_lb.LoadBalancerType.REGIONAL_EXTERNAL_APPLICATION_LB)
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[5]]}}
    step = LbErrorRateCheck(average_request_count=100)
    with op.operator_context(self.operator):
      step.execute()
    query_str = mock_query.call_args[0][1]
    self.assertIn('http_external_regional_lb_rule', query_str)
    self.assertIn(f"resource.forwarding_rule_name == '{self.mock_fr.name}'",
                  query_str)
    self.assertIn(
        f"resource.region == '{self.operator.parameters[flags.REGION]}'",
        query_str)

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_error_rate_empty_values(self, mock_get_fr, mock_query):
    """Covers  Handling missing 'values' key in LbErrorRateCheck."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'other': 'data'}}
    step = LbErrorRateCheck(average_request_count=10)
    with op.operator_context(self.operator):
      step.execute()

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  def test_error_rate_zero_qps(self, mock_get_fr, mock_query):
    """Covers  Error rate calculation when request count is zero."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.return_value = {'key': {'values': [[5]]}}
    step = LbErrorRateCheck(average_request_count=0)
    with op.operator_context(self.operator):
      step.execute()

  @mock.patch('gcpdiag.queries.monitoring.query')
  @mock.patch('gcpdiag.queries.lb.get_forwarding_rule')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_error_rate_exception(self, mock_info, mock_get_fr, mock_query):
    """Covers  Exception handling in LbErrorRateCheck."""
    mock_get_fr.return_value = self.mock_fr
    mock_query.side_effect = RuntimeError('Monitoring Error')
    step = LbErrorRateCheck(average_request_count=10)
    with op.operator_context(self.operator):
      with self.assertRaises(RuntimeError):
        step.execute()
    mock_info.assert_any_call(mock.ANY)
