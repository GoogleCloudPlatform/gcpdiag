# Copyright 2025 Google LLC
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
"""Tests for generalized_steps.py."""

import datetime
import re
import tempfile
import unittest
from unittest import mock

import apiclient.errors

from gcpdiag import utils
from gcpdiag.queries import apis_stub, gce
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, generalized_steps
from gcpdiag.runbook.gcp import flags
from gcpdiag.runbook.iam import flags as iam_flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs
from gcpdiag.runbook.logs import generalized_steps as logs_gs

DUMMY_PROJECT_ID = 'gcpdiag-gce1-aaaa'


class RegexMatcher:
  """A matcher that checks if a string matches a regex."""

  def __init__(self, pattern):
    self.pattern = re.compile(pattern)

  def __eq__(self, other):
    return isinstance(other, str) and bool(self.pattern.search(other))

  def __repr__(self):
    return f'<RegexMatcher pattern={self.pattern.pattern}>'


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GceStepTestBase(unittest.TestCase):
  """Base class for GCE generalized step tests using a real Operator context."""

  def setUp(self):
    super().setUp()
    self.mock_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))

    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()

    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()

    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.ZONE:
            'us-central1-a',
        flags.INSTANCE_NAME:
            'test-instance',
        flags.INSTANCE_ID:
            '12345',
        flags.START_TIME:
            datetime.datetime(2025, 10, 27, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 10, 28, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params

    self.mock_instance = mock.Mock(spec=gce.Instance)
    self.mock_instance.project_id = DUMMY_PROJECT_ID
    self.mock_instance.zone = 'us-central1-a'
    self.mock_instance.name = 'test-instance'
    self.mock_instance.id = '12345'
    self.mock_instance.full_path = (
        f'projects/{DUMMY_PROJECT_ID}/zones/us-central1-a/'
        'instances/test-instance')
    self.mock_instance.machine_type = mock.Mock(return_value='n1-standard-1')

    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance',
                   return_value=self.mock_instance))


class GeneralizedStepsUtilsTest(unittest.TestCase):
  """Tests for private utility functions and edge cases."""

  def test_get_operator_fn_error(self):
    with self.assertRaises(ValueError):
      # pylint: disable=protected-access
      generalized_steps._get_operator_fn('invalid')

  def test_resolve_expected_value_ref_fail(self):
    with self.assertRaises(ValueError):
      # pylint: disable=protected-access
      generalized_steps._resolve_expected_value('ref:MISSING_CONST')

  def test_check_condition_contains_non_collection(self):
    # pylint: disable=protected-access
    assert not generalized_steps._check_condition(123, '1', 'contains')

  def test_check_condition_matches_invalid_regex(self):
    with self.assertRaises(ValueError):
      # pylint: disable=protected-access
      generalized_steps._check_condition('text', '[', 'matches')

  def test_check_condition_type_mismatch(self):
    # pylint: disable=protected-access
    assert not generalized_steps._check_condition({}, 1, 'lt')


class HighVmMemoryUtilizationTest(GceStepTestBase):
  """Test HighVmMemoryUtilization step."""

  def test_init_with_vm_object(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch('gcpdiag.queries.monitoring.query', return_value=[]),
      ):
        step = generalized_steps.HighVmMemoryUtilization()
        step.vm = self.mock_instance
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_ops_agent_installed_memory_usage_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch(
              'gcpdiag.queries.monitoring.query',
              return_value=[{
                  'metric': 'data'
              }],
          ),
      ):
        step = generalized_steps.HighVmMemoryUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        run_id='test-run',
        resource=self.mock_instance,
        reason='failure_reason',
        remediation='failure_remediation',
        step_execution_id=mock.ANY,
    )

  def test_ops_agent_not_installed_not_e2_skipped(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                      return_value=False):
        step = generalized_steps.HighVmMemoryUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.info.assert_called_with(
        message=RegexMatcher('.*not export memory metrics.*'), step_type='INFO')
    self.mock_interface.add_skipped.assert_called_once()

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch(
          'gcpdiag.runbook.gce.util.ensure_instance_resolved',
          side_effect=runbook_exceptions.FailedStepError('err'),
      ):
        step = generalized_steps.HighVmMemoryUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.HighVmMemoryUtilization()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_cpu_usage_not_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=False),
          mock.patch('gcpdiag.queries.monitoring.query', return_value=[]),
      ):
        step = generalized_steps.HighVmCpuUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_e2_machine_memory_usage_found(self):
    self.mock_instance.machine_type.return_value = 'e2-medium'
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=False),
          mock.patch(
              'gcpdiag.queries.monitoring.query',
              return_value=[{
                  'metric': 'data'
              }],
          ),
      ):
        step = generalized_steps.HighVmMemoryUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()


class HighVmDiskUtilizationTest(GceStepTestBase):
  """Test HighVmDiskUtilization step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.HighVmDiskUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.HighVmDiskUtilization()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_init_with_vm_object(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch('gcpdiag.queries.monitoring.query', return_value=[]),
      ):
        step = generalized_steps.HighVmDiskUtilization()
        step.vm = self.mock_instance
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_ops_agent_installed_disk_usage_not_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch('gcpdiag.queries.monitoring.query', return_value=[]),
      ):
        step = generalized_steps.HighVmDiskUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once_with(
        run_id='test-run',
        resource=self.mock_instance,
        reason='success_reason',
        step_execution_id=mock.ANY,
    )

  def test_ops_agent_installed_disk_usage_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch(
              'gcpdiag.queries.monitoring.query',
              return_value=[{
                  'metric': 'data'
              }],
          ),
      ):
        step = generalized_steps.HighVmDiskUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once_with(
        run_id='test-run',
        resource=self.mock_instance,
        reason='failure_reason',
        remediation='failure_remediation',
        step_execution_id=mock.ANY,
    )

  def test_no_ops_agent_skipped_with_child_step(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=False),
          mock.patch('gcpdiag.queries.monitoring.query', return_value=[]),
      ):
        step = generalized_steps.HighVmDiskUtilization()
        step.vm = self.mock_instance
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    assert any(
        isinstance(c, generalized_steps.VmSerialLogsCheck) for c in step.steps)


class HighVmCpuUtilizationTest(GceStepTestBase):
  """Test HighVmCpuUtilization step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.HighVmCpuUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_init_with_vm_object(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed', return_value=True), \
           mock.patch('gcpdiag.queries.monitoring.query', return_value=[]):
        step = generalized_steps.HighVmCpuUtilization()
        step.vm = self.mock_instance
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_cpu_usage_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=False),
          mock.patch(
              'gcpdiag.queries.monitoring.query',
              return_value=[{
                  'metric': 'data'
              }],
          ),
      ):
        step = generalized_steps.HighVmCpuUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_ops_agent_installed_cpu_usage_found(self):
    with op.operator_context(self.operator):
      with (
          mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed',
                     return_value=True),
          mock.patch(
              'gcpdiag.queries.monitoring.query',
              return_value=[{
                  'metric': 'data'
              }],
          ),
      ):
        step = generalized_steps.HighVmCpuUtilization()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.HighVmCpuUtilization()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class GceVpcConnectivityCheckTest(GceStepTestBase):
  """Test GceVpcConnectivityCheck step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.GceVpcConnectivityCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.GceVpcConnectivityCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_init_with_vm_object(self):
    self.mock_instance.network.firewall.check_connectivity_ingress.return_value = mock.Mock(
        action='allow', matched_by_str='firewall-rule-1')
    with op.operator_context(self.operator):
      step = generalized_steps.GceVpcConnectivityCheck()
      step.vm = self.mock_instance
      step.traffic = 'ingress'
      step.src_ip = '1.2.3.4'
      step.protocol_type = 'tcp'
      step.port = 443
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_ingress_deny(self):
    self.mock_instance.network.firewall.check_connectivity_ingress.return_value = mock.Mock(
        action='deny', matched_by_str='firewall-rule-2')
    with op.operator_context(self.operator):
      step = generalized_steps.GceVpcConnectivityCheck()
      step.traffic = 'ingress'
      step.src_ip = '1.2.3.4'
      step.protocol_type = 'tcp'
      step.port = 443
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_egress_allow(self):
    self.mock_instance.network_ips = ['10.0.0.1']
    self.mock_instance.network.firewall.check_connectivity_egress.return_value = mock.Mock(
        action='allow', matched_by_str='firewall-rule-1')
    with op.operator_context(self.operator):
      step = generalized_steps.GceVpcConnectivityCheck()
      step.traffic = 'egress'
      step.src_ip = '10.0.0.1'
      step.protocol_type = 'tcp'
      step.port = 80
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()


class VmScopeTest(GceStepTestBase):
  """Test VmScope step."""

  def test_require_all_false_fail(self):
    self.mock_instance.access_scopes = {'scope3'}
    with op.operator_context(self.operator):
      step = generalized_steps.VmScope()
      step.access_scopes = {'scope1', 'scope2'}
      step.require_all = False
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_require_all_true_fail(self):
    self.mock_instance.access_scopes = {'scope1'}
    with op.operator_context(self.operator):
      step = generalized_steps.VmScope()
      step.access_scopes = {'scope1', 'scope2'}
      step.require_all = True
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.VmScope()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.VmScope()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_init_with_vm_object(self):
    self.mock_instance.access_scopes = {'scope1'}
    with op.operator_context(self.operator):
      step = generalized_steps.VmScope()
      step.vm = self.mock_instance
      step.access_scopes = {'scope1'}
      step.require_all = False
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_require_all_ok(self):
    self.mock_instance.access_scopes = {'scope1', 'scope2'}
    with op.operator_context(self.operator):
      step = generalized_steps.VmScope()
      step.access_scopes = {'scope1', 'scope2'}
      step.require_all = True
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()


class GceLogCheckTest(GceStepTestBase):
  """Test GceLogCheck step."""

  def test_missing_project_id(self):
    self.params.pop(flags.PROJECT_ID, None)
    self.params['filter_str'] = 'test-filter'
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_gce_log_check_adds_child(self):
    self.params['filter_str'] = 'test-filter'
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      step.execute()
    assert any(isinstance(c, logs_gs.CheckIssueLogEntry) for c in step.steps)

  def test_gce_log_check_ref_resolution(self):
    constants.TEST_FILTER = 'filter-from-ref'
    self.params['filter_str'] = 'ref:TEST_FILTER'
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(
        c for c in step.steps if isinstance(c, logs_gs.CheckIssueLogEntry))
    self.assertEqual(child.filter_str, 'filter-from-ref')
    del constants.TEST_FILTER

  def test_gce_log_check_invalid_ref(self):
    self.params['filter_str'] = 'ref:INVALID_FILTER_REF'
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.InvalidParameterError):
        step.execute()

  def test_parameter_missing(self):
    self.params.pop('filter_str', None)
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_gce_log_check_issue_pattern_ref_resolution(self):
    constants.TEST_PATTERN = ['pattern1', 'pattern2']
    self.params['filter_str'] = 'some-filter'
    self.params['issue_pattern'] = 'ref:TEST_PATTERN'
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(
        c for c in step.steps if isinstance(c, logs_gs.CheckIssueLogEntry))
    self.assertEqual(child.issue_pattern, ['pattern1', 'pattern2'])
    del constants.TEST_PATTERN

  def test_no_issue_pattern(self):
    self.params['filter_str'] = 'some-filter'
    self.params.pop('issue_pattern', None)
    with op.operator_context(self.operator):
      step = generalized_steps.GceLogCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(
        c for c in step.steps if isinstance(c, logs_gs.CheckIssueLogEntry))
    self.assertEqual(child.issue_pattern, [])


class VmHasOpsAgentTest(GceStepTestBase):
  """Test VmHasOpsAgent step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.VmHasOpsAgent()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_subagent_check_with_metrics(self):
    step = generalized_steps.VmHasOpsAgent()
    metric_data = {
        'a': {
            'labels': {
                'metric.version': 'google-cloud-ops-agent-metrics-1'
            }
        },
        'b': {
            'labels': {
                'metric.version': 'google-cloud-ops-agent-logging-1'
            }
        }
    }
    # pylint: disable=protected-access
    self.assertEqual(step._has_ops_agent_subagent(metric_data), {
        'metrics_subagent_installed': True,
        'logging_subagent_installed': True
    })

  def test_logging_agent_fail(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.logs.realtime_query', return_value=[]):
        step = generalized_steps.VmHasOpsAgent()
        step.check_metrics = False
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_metrics_agent_fail(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.monitoring.query', return_value={}):
        step = generalized_steps.VmHasOpsAgent()
        step.check_logging = False
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_subagent_check_no_metrics(self):
    step = generalized_steps.VmHasOpsAgent()
    # pylint: disable=protected-access
    self.assertEqual(step._has_ops_agent_subagent(None), {
        'metrics_subagent_installed': False,
        'logging_subagent_installed': False
    })

  def test_init_with_vm_object(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.logs.realtime_query',
                      return_value=[{
                          'log': 'data'
                      }]):
        step = generalized_steps.VmHasOpsAgent()
        step.vm = self.mock_instance
        step.check_metrics = False
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_logging_agent_ok(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.logs.realtime_query',
                      return_value=[{
                          'log': 'data'
                      }]):
        step = generalized_steps.VmHasOpsAgent()
        step.check_metrics = False
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()


class VmLifecycleStateTest(GceStepTestBase):
  """Test VmLifecycleState step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.VmLifecycleState()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.VmLifecycleState()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_init_with_vm_object(self):
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.VmLifecycleState()
      step.vm = self.mock_instance
      step.expected_lifecycle_status = 'RUNNING'
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_running_state_ok(self):
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.VmLifecycleState()
      step.expected_lifecycle_status = 'RUNNING'
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_non_running_state_failed(self):
    self.mock_instance.status = 'TERMINATED'
    with op.operator_context(self.operator):
      step = generalized_steps.VmLifecycleState()
      step.expected_lifecycle_status = 'RUNNING'
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()


class GceIamPolicyCheckTest(GceStepTestBase):
  """Test GceIamPolicyCheck step."""

  def test_gce_iam_policy_check_adds_child(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['roles'] = 'roles/viewer'
    with op.operator_context(self.operator):
      step = generalized_steps.GceIamPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    assert any(isinstance(c, iam_gs.IamPolicyCheck) for c in step.steps)

  def test_iam_role_ref_resolution(self):
    # Coverage for ref: in IAM roles
    constants.TEST_ROLE = 'roles/owner'
    self.params.update({
        iam_flags.PRINCIPAL: 'u@g.com',
        'roles': 'ref:TEST_ROLE'
    })
    with op.operator_context(self.operator):
      step = generalized_steps.GceIamPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(c for c in step.steps if isinstance(c, iam_gs.IamPolicyCheck))
    assert 'roles/owner' in child.roles
    del constants.TEST_ROLE

  def test_iam_permission_ref_resolution(self):
    constants.TEST_PERMS = ['p1', 'p2']
    self.params.update({
        iam_flags.PRINCIPAL: 'u@g.com',
        'permissions': 'ref:TEST_PERMS'
    })
    with op.operator_context(self.operator):
      step = generalized_steps.GceIamPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(c for c in step.steps if isinstance(c, iam_gs.IamPolicyCheck))
    self.assertEqual(child.permissions, {'p1', 'p2'})
    del constants.TEST_PERMS

  def test_gce_iam_policy_check_only_roles(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['roles'] = 'roles/viewer'
    self.params.pop('permissions', None)
    with op.operator_context(self.operator):
      step = generalized_steps.GceIamPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    child = next(c for c in step.steps if isinstance(c, iam_gs.IamPolicyCheck))
    self.assertEqual(child.roles, {'roles/viewer'})
    self.assertIsNone(child.permissions)


class MigAutoscalingPolicyCheckTest(GceStepTestBase):
  """Test MigAutoscalingPolicyCheck step."""

  def test_get_instance_api_error_non_404(self):
    err = apiclient.errors.HttpError(mock.Mock(status=500), b'server error')
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance', side_effect=err):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        with self.assertRaises(utils.GcpApiError):
          step.execute()

  def test_missing_property_path(self):
    self.mock_instance.created_by_mig = False
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.params['property_path'] = None
    self.params['expected_value'] = 'v'
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_missing_expected_value(self):
    self.params['property_path'] = 'p'
    self.params['expected_value'] = None
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_bad_ref_expected_value(self):
    self.params['property_path'] = 'p'
    self.params['expected_value'] = 'ref:MISSING'
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.InvalidParameterError):
        step.execute()

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance', return_value=None):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_check_autoscaler_policy_ok(self):
    self.params.update({
        'property_path': 'autoscalingPolicy.mode',
        'expected_value': 'ON',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.zone = 'us-central1-a'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    mock_autoscaler = mock.Mock()
    mock_autoscaler.get.return_value = 'ON'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_autoscaler',
                      return_value=mock_autoscaler):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()
    mock_autoscaler.get.assert_called_with('autoscalingPolicy.mode',
                                           default=None)

  def test_check_autoscaler_policy_404_fail(self):
    self.params.update({
        'property_path': 'autoscalingPolicy.mode',
        'expected_value': 'ON',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.zone = 'us-central1-a'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    err = apiclient.errors.HttpError(mock.Mock(status=404), b'not found')
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_autoscaler', side_effect=err):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_check_policy_by_instance_ok(self):
    self.params.update({
        'property_path': 'some_property',
        'expected_value': 'some_value',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_check_policy_by_instance_fail(self):
    self.params.update({
        'property_path': 'some_property',
        'expected_value': 'other_value',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_instance_not_in_mig(self):
    self.mock_instance.created_by_mig = False
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called()

  def test_regional_mig_policy_ok(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        'mig_name': 'm',
        'location': 'us-central1',
        'property_path': 'p',
        'expected_value': 'v'
    })
    mock_mig = mock.Mock()
    mock_mig.region = 'us-central1'
    mock_mig.zone = None
    mock_mig.name = 'm'
    mock_mig.get.return_value = 'v'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_region_instance_group_manager',
                      return_value=mock_mig):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_check_regional_autoscaler_policy_ok(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        'mig_name': 'regional-mig',
        'location': 'us-central1',
        'property_path': 'autoscalingPolicy.mode',
        'expected_value': 'ON',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'regional-mig'
    mock_mig.region = 'us-central1'
    mock_mig.zone = None
    mock_autoscaler = mock.Mock()
    mock_autoscaler.get.return_value = 'ON'
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_region_instance_group_manager',
              return_value=mock_mig,
          ),
          mock.patch(
              'gcpdiag.queries.gce.get_region_autoscaler',
              return_value=mock_autoscaler,
          ),
      ):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_check_zonal_autoscaler_policy_ok(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        'mig_name': 'zonal-mig',
        'location': 'us-central1-a',
        'property_path': 'p',
        'expected_value': 'v'
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'zonal-mig'
    mock_mig.zone = 'us-central1-a'
    mock_mig.get.return_value = 'v'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance_group_manager',
                      return_value=mock_mig):
        step = generalized_steps.MigAutoscalingPolicyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_mig_location_missing_skipped(self):
    self.params.update({
        'property_path': 'some_property',
        'expected_value': 'some_value',
    })
    mock_mig = mock.Mock()
    mock_mig.name = 'test-mig'
    mock_mig.zone = None
    mock_mig.region = None
    mock_mig.get.return_value = 'some_value'
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = mock_mig
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_mig_invalid_location_raises_error(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        'mig_name': 'm',
        'location': 'invalid-location-format',
        'property_path': 'p',
        'expected_value': 'v'
    })
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      with self.assertRaises(FileNotFoundError):
        step.execute()


class VmSerialLogsCheckTest(GceStepTestBase):
  """Test VmSerialLogsCheck step."""

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.VmSerialLogsCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.VmSerialLogsCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_pattern_overrides(self):
    self.params['template'] = 't'
    self.params['positive_patterns'] = 'p1'
    self.params['negative_patterns'] = 'n1'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance_serial_port_output',
                      return_value=mock.Mock(contents='n1 line')), \
          mock.patch('gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
                     side_effect=[False, True]):
        step = generalized_steps.VmSerialLogsCheck()
        self.operator.set_step(step)
        step.execute()
    self.assertEqual(step.template, 't')
    self.assertEqual(step.positive_pattern, ['p1'])
    self.assertEqual(step.negative_pattern, ['n1'])
    self.mock_interface.add_failed.assert_called_once()

  def test_pattern_overrides_with_ref(self):
    constants.TEST_P_PATTERNS = ['p1', 'p2']
    constants.TEST_N_PATTERNS = ['n1']
    self.params['positive_patterns'] = 'ref:TEST_P_PATTERNS'
    self.params['negative_patterns'] = 'ref:TEST_N_PATTERNS'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance_serial_port_output',
                      return_value=mock.Mock(contents='n1 line')), \
          mock.patch('gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
                     side_effect=[False, True]):
        step = generalized_steps.VmSerialLogsCheck()
        self.operator.set_step(step)
        step.execute()
    self.assertEqual(step.positive_pattern, ['p1', 'p2'])
    self.assertEqual(step.negative_pattern, ['n1'])
    self.mock_interface.add_failed.assert_called_once()
    del constants.TEST_P_PATTERNS
    del constants.TEST_N_PATTERNS

  def test_init_with_vm_object(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='some serial log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=True,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.vm = self.mock_instance
        step.positive_pattern = ['success']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_positive_pattern_ok(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='some serial log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=True,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.positive_pattern = ['success']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_negative_pattern_fail(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='error log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              side_effect=[False, True],
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.positive_pattern = ['success']
        step.negative_pattern = ['error']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_no_pattern_uncertain(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='some log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=False,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.positive_pattern = ['success']
        step.negative_pattern = ['error']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_positive_only_no_match_uncertain(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='some log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=False,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.positive_pattern = ['success']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_negative_only_no_match_uncertain(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='some log'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=False,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.negative_pattern = ['error']
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_no_logs_skipped(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance_serial_port_output',
                      return_value=None):
        step = generalized_steps.VmSerialLogsCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_serial_console_file_read_ok(self):
    # Create a dummy file to read
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as f:
      f.write('success line')
      f.flush()
      with op.operator_context(self.operator):
        with mock.patch(
            'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
            return_value=True,
        ):
          step = generalized_steps.VmSerialLogsCheck()
          step.positive_pattern = ['success']
          step.serial_console_file = f.name
          self.operator.set_step(step)
          step.execute()
      self.mock_interface.add_ok.assert_called_once()

  def test_serial_console_multiple_files(self):
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8') as f1, tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8') as f2:
      f1.write('success line 1')
      f1.flush()
      f2.write('success line 2')
      f2.flush()
      with op.operator_context(self.operator):
        with mock.patch(
            'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
            return_value=True,
        ):
          step = generalized_steps.VmSerialLogsCheck()
          step.positive_pattern = ['success']
          step.serial_console_file = f'{f1.name},{f2.name}'
          self.operator.set_step(step)
          step.execute()
      self.mock_interface.add_ok.assert_called_once()

  def test_positive_pattern_and_operator_ok(self):
    with op.operator_context(self.operator):
      with (
          mock.patch(
              'gcpdiag.queries.gce.get_instance_serial_port_output',
              return_value=mock.Mock(contents='success1 success2'),
          ),
          mock.patch(
              'gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
              return_value=True,
          ),
      ):
        step = generalized_steps.VmSerialLogsCheck()
        step.positive_pattern = ['success1', 'success2']
        step.positive_pattern_operator = 'AND'
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_parameter_overrides_only_template(self):
    self.params['template'] = 't'
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.queries.gce.get_instance_serial_port_output',
                      return_value=mock.Mock(contents='some log')), \
          mock.patch('gcpdiag.runbook.gce.util.search_pattern_in_serial_logs',
                     return_value=False):
        step = generalized_steps.VmSerialLogsCheck()
        self.operator.set_step(step)
        step.execute()
    self.assertEqual(step.template, 't')


class VmMetadataCheckTest(GceStepTestBase):
  """Test VmMetadataCheck step."""

  def test_instance_resolution_failure(self):
    self.params.update({
        'metadata_key': 'k',
        'expected_value': 'v',
    })
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.VmMetadataCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_expected_value_ref_resolution_fail(self):
    self.params.update({
        'metadata_key': 'k',
        'expected_value': 'ref:MISSING_VALUE',
    })
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.InvalidParameterError):
        step.execute()

  def test_init_with_vm_object(self):
    self.params.update({
        'metadata_key': 'enable-oslogin',
        'expected_value': 'true',
    })
    self.mock_instance.get_metadata.return_value = 'true'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      step.vm = self.mock_instance
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_metadata_bool_true_ok(self):
    self.params.update({
        'metadata_key': 'enable-oslogin',
        'expected_value': 'true',
    })
    self.mock_instance.get_metadata.return_value = 'true'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_metadata_bool_fail(self):
    self.params.update({
        'metadata_key': 'enable-oslogin',
        'expected_value': 'true',
    })
    self.mock_instance.get_metadata.return_value = 'false'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_bool_expected_false_ok(self):
    self.params.update({
        'metadata_key': 'enable-oslogin',
        'expected_value': 'false',
    })
    self.mock_instance.get_metadata.return_value = 'false'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_metadata_string_ok(self):
    self.params.update({
        'metadata_key': 'startup-script',
        'expected_value': 'echo hello',
    })
    self.mock_instance.get_metadata.return_value = 'echo hello'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_metadata_numeric_comparison(self):
    constants.TEST_NUM = 10.5
    self.params.update({'metadata_key': 'k', 'expected_value': 'ref:TEST_NUM'})
    self.mock_instance.get_metadata.return_value = 10.50000001
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    del constants.TEST_NUM

  def test_metadata_api_error_404(self):
    self.params.update({'metadata_key': 'k', 'expected_value': 'v'})
    err = apiclient.errors.HttpError(mock.Mock(status=404), b'not found')
    self.mock_gce_get_instance.side_effect = err
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_metadata_key_ref_resolution(self):
    constants.TEST_KEY = 'startup-script'
    self.params.update({
        'metadata_key': 'ref:TEST_KEY',
        'expected_value': 'echo hello',
    })
    self.mock_instance.get_metadata.return_value = 'echo hello'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.mock_instance.get_metadata.assert_called_with('startup-script')
    del constants.TEST_KEY

  def test_metadata_key_ref_resolution_fail(self):
    self.params.update({
        'metadata_key': 'ref:MISSING_KEY',
        'expected_value': 'echo hello',
    })
    self.mock_instance.get_metadata.return_value = 'echo hello'
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      with self.assertRaises(AttributeError):
        step.execute()

  def test_metadata_api_error_non_404(self):
    self.params.update({'metadata_key': 'k', 'expected_value': 'v'})
    err = apiclient.errors.HttpError(mock.Mock(status=500), b'server error')
    self.mock_gce_get_instance.side_effect = err
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      with self.assertRaises(utils.GcpApiError):
        step.execute()

  def test_missing_metadata_key_raises_error(self):
    self.params.update({'expected_value': 'v'})
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_missing_expected_value_raises_error(self):
    self.params.update({'metadata_key': 'k'})
    with op.operator_context(self.operator):
      step = generalized_steps.VmMetadataCheck()
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()


class InstancePropertyCheckTest(GceStepTestBase):
  """Test InstancePropertyCheck step."""

  def test_invalid_property_path(self):
    self.params.update({
        'property_path': 'invalid_property',
        'expected_value': 'RUNNING',
    })
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      with self.assertRaises(ValueError):
        step.execute()

  def test_instance_resolution_failure(self):
    with op.operator_context(self.operator):
      with mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved',
                      side_effect=runbook_exceptions.FailedStepError('err')):
        step = generalized_steps.InstancePropertyCheck()
        self.operator.set_step(step)
        step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_vm_not_found(self):
    self.params['property_path'] = 'status'
    self.params['expected_value'] = 'RUNNING'
    err = apiclient.errors.HttpError(mock.Mock(status=404), b'not found')
    self.mock_gce_get_instance.side_effect = err
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.params.pop('property_path', None)
    self.params.pop('expected_value', None)

  def test_init_with_vm_object(self):
    self.params.update({
        'property_path': 'status',
        'expected_value': 'RUNNING',
    })
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      step.vm = self.mock_instance
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_property_eq_ok(self):
    self.params.update({
        'property_path': 'status',
        'expected_value': 'RUNNING',
    })
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_property_ne_fail(self):
    self.params.update({
        'property_path': 'status',
        'expected_value': 'TERMINATED',
        'operator': 'ne'
    })
    self.mock_instance.status = 'TERMINATED'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_property_path_ref_resolution(self):
    constants.STATUS_PROP = 'status'
    self.params.update({
        'property_path': 'ref:STATUS_PROP',
        'expected_value': 'RUNNING',
    })
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    del constants.STATUS_PROP

  def test_property_matches_ok(self):
    self.params.update({
        'property_path': 'name',
        'expected_value': r'test-.+',
        'operator': 'matches',
    })
    self.mock_instance.name = 'test-instance'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_property_matches_list_ok(self):
    self.params.update({
        'property_path': 'boot_disk_licenses',
        'expected_value': r'rhel-8',
        'operator': 'matches',
    })
    self.mock_instance.boot_disk_licenses = ['rhel-8-sap', 'other-license']
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_property_contains_list_ok(self):
    self.params.update({
        'property_path': 'boot_disk_licenses',
        'expected_value': 'rhel-8-sap',
        'operator': 'contains',
    })
    self.mock_instance.boot_disk_licenses = ['rhel-8-sap', 'other-license']
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_get_instance_api_error_non_404(self):
    self.params.update({'property_path': 'status', 'expected_value': 'RUNNING'})
    err = apiclient.errors.HttpError(mock.Mock(status=500), b'server error')
    self.mock_gce_get_instance.side_effect = err
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      with self.assertRaises(utils.GcpApiError):
        step.execute()

  def test_missing_property_path_raises_error(self):
    self.params.pop('property_path', None)
    self.params.update({'expected_value': 'v'})
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      step.property_path = None
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()

  def test_missing_expected_value_raises_error(self):
    self.params.pop('expected_value', None)
    self.params.update({'property_path': 'status'})
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      step.expected_value = None
      self.operator.set_step(step)
      with self.assertRaises(runbook_exceptions.MissingParameterError):
        step.execute()


class StepParameterResolutionTest(GceStepTestBase):
  """Tests focusing on parameter resolution and 'vm not found' paths."""

  def test_step_parameter_override(self):
    self.params['property_path'] = 'status'
    self.params['expected_value'] = 'RUNNING'
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.params.pop('property_path', None)
    self.params.pop('expected_value', None)

  def test_step_parameter_ref_resolution_override(self):
    constants.TEST_VALUE = 'RUNNING'
    self.params['property_path'] = 'status'
    self.params['expected_value'] = 'ref:TEST_VALUE'
    self.mock_instance.status = 'RUNNING'
    with op.operator_context(self.operator):
      step = generalized_steps.InstancePropertyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.params.pop('property_path', None)
    self.params.pop('expected_value', None)
    del constants.TEST_VALUE

  def test_vm_not_found_skips(self):
    # INSTANCE_ID in self.params prevents AttributeError in resolution logic.
    self.mock_gce_get_instance.return_value = None
    with op.operator_context(self.operator):
      step = generalized_steps.VmLifecycleState()
      step.expected_lifecycle_status = 'RUNNING'
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    _, kwargs = self.mock_interface.add_skipped.call_args
    self.assertIn('not found in project', kwargs['reason'])


class ExtendedEdgeCaseTest(GceStepTestBase):
  """Tests for specific edge cases in logic flow."""

  def test_mig_autoscaling_policy_missing_mig(self):
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = None  # Trigger AttributeError branch
    self.params.update({'property_path': 'foo', 'expected_value': 'bar'})
    with op.operator_context(self.operator):
      step = generalized_steps.MigAutoscalingPolicyCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called()
