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
import unittest
from unittest import mock

import apiclient.errors

from gcpdiag.queries import gce
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import op
from gcpdiag.runbook.gce import constants, generalized_steps
from gcpdiag.runbook.gcp import flags
from gcpdiag.runbook.iam import flags as iam_flags


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class GceStepTestBase(unittest.TestCase):
  """Base class for GCE generalized step tests."""

  def setUp(self):
    super().setUp()
    # enterContext will automatically clean up the patch
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_add_ok = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_ok'))
    self.mock_op_add_failed = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_failed'))
    self.mock_op_add_skipped = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_skipped'))
    self.mock_op_add_metadata = self.enterContext(
        mock.patch('gcpdiag.runbook.op.add_metadata'))
    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))
    self.mock_ensure_instance_resolved = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved'))

    self.mock_instance = mock.Mock(spec=gce.Instance)
    self.mock_instance.project_id = 'test-project'
    self.mock_instance.zone = 'us-central1-a'
    self.mock_instance.name = 'test-instance'
    self.mock_instance.id = '12345'
    self.mock_gce_get_instance.return_value = self.mock_instance

    # Default side effect for op.get
    self.params = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.START_TIME: datetime.datetime(2025, 10, 27),
        flags.END_TIME: datetime.datetime(2025, 10, 28),
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)

    # Setup operator context
    mock_interface = mock.Mock()
    operator = op.Operator(mock_interface)
    operator.messages = MockMessage()
    operator.parameters = self.params
    self.enterContext(op.operator_context(operator))


class HighVmDiskUtilizationTest(GceStepTestBase):
  """Test HighVmDiskUtilization step."""

  def setUp(self):
    super().setUp()
    self.ops_agent_installed_patch = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed'))
    self.monitoring_query_patch = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.vm_serial_logs_check_patch = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmSerialLogsCheck',
                   autospec=True))
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.HighVmDiskUtilization.add_child'
        ))

  def test_ops_agent_installed_disk_usage_found(self):
    self.ops_agent_installed_patch.return_value = True
    self.monitoring_query_patch.return_value = [{'metric': 'data'}]
    step = generalized_steps.HighVmDiskUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_failed.assert_called_once()

  def test_ops_agent_installed_disk_usage_not_found(self):
    self.ops_agent_installed_patch.return_value = True
    self.monitoring_query_patch.return_value = []
    step = generalized_steps.HighVmDiskUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_ops_agent_not_installed(self):
    self.ops_agent_installed_patch.return_value = False
    step = generalized_steps.HighVmDiskUtilization()
    step.execute()
    self.monitoring_query_patch.assert_not_called()
    self.mock_op_add_skipped.assert_called_once()
    self.add_child_patch.assert_called_once()


class HighVmCpuUtilizationTest(GceStepTestBase):
  """Test HighVmCpuUtilization step."""

  def setUp(self):
    super().setUp()
    self.ops_agent_installed_patch = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.util.ops_agent_installed'))
    self.monitoring_query_patch = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))

  def test_ops_agent_not_installed_cpu_usage_found(self):
    self.ops_agent_installed_patch.return_value = False
    self.monitoring_query_patch.return_value = [{'metric': 'data'}]
    step = generalized_steps.HighVmCpuUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_failed.assert_called_once()

  def test_ops_agent_installed_cpu_usage_found(self):
    self.ops_agent_installed_patch.return_value = True
    self.monitoring_query_patch.return_value = [{'metric': 'data'}]
    step = generalized_steps.HighVmCpuUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_failed.assert_called_once()

  def test_ops_agent_installed_cpu_usage_not_found(self):
    self.ops_agent_installed_patch.return_value = True
    self.monitoring_query_patch.return_value = []
    step = generalized_steps.HighVmCpuUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_failed.assert_not_called()
    self.mock_op_add_ok.assert_called_once()

  def test_ops_agent_not_installed_cpu_usage_not_found(self):
    self.ops_agent_installed_patch.return_value = False
    self.monitoring_query_patch.return_value = []
    step = generalized_steps.HighVmCpuUtilization()
    step.execute()
    self.monitoring_query_patch.assert_called_once()
    self.mock_op_add_failed.assert_not_called()
    self.mock_op_add_ok.assert_called_once()


class GceVpcConnectivityCheckTest(GceStepTestBase):
  """Test GceVpcConnectivityCheck step."""

  def test_ingress_deny(self):
    step = generalized_steps.GceVpcConnectivityCheck()
    step.traffic = 'ingress'
    step.src_ip = '1.2.3.4'
    step.protocol_type = 'tcp'
    step.port = 443
    self.mock_instance.network.firewall.check_connectivity_ingress.return_value = mock.Mock(
        action='deny', matched_by_str='firewall-rule-2')
    step.execute()
    self.mock_instance.network.firewall.check_connectivity_ingress.assert_called_once(
    )
    self.mock_op_add_failed.assert_called_once()

  def test_ingress_allow(self):
    step = generalized_steps.GceVpcConnectivityCheck()
    step.traffic = 'ingress'
    step.src_ip = '1.2.3.4'
    step.protocol_type = 'tcp'
    step.port = 22
    self.mock_instance.network.firewall.check_connectivity_ingress.return_value = mock.Mock(
        action='allow', matched_by_str='firewall-rule-1')
    step.execute()
    self.mock_instance.network.firewall.check_connectivity_ingress.assert_called_once(
    )
    self.mock_op_add_ok.assert_called_once()

  def test_egress_allow(self):
    step = generalized_steps.GceVpcConnectivityCheck()
    step.traffic = 'egress'
    step.src_ip = '10.0.0.2'
    step.protocol_type = 'tcp'
    step.port = 80
    self.mock_instance.network.firewall.check_connectivity_egress.return_value = mock.Mock(
        action='allow', matched_by_str='firewall-rule-3')
    step.execute()
    self.mock_instance.network.firewall.check_connectivity_egress.assert_called_once(
    )
    self.mock_op_add_ok.assert_called_once()


class VmScopeTest(GceStepTestBase):
  """Test VmScope step."""

  def setUp(self):
    super().setUp()
    self.mock_instance.access_scopes = {'scope1', 'scope2'}

  def test_require_all_failed(self):
    step = generalized_steps.VmScope()
    step.access_scopes = {'scope1', 'scope3'}
    step.require_all = True
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_require_all_ok(self):
    step = generalized_steps.VmScope()
    step.access_scopes = {'scope1', 'scope2'}
    step.require_all = True
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_require_any_ok(self):
    step = generalized_steps.VmScope()
    step.access_scopes = {'scope1', 'scope3'}
    step.require_all = False
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_require_any_failed(self):
    step = generalized_steps.VmScope()
    step.access_scopes = {'scope3', 'scope4'}
    step.require_all = False
    step.execute()
    self.mock_op_add_failed.assert_called_once()


class GceLogCheckTest(GceStepTestBase):
  """Test GceLogCheck step."""

  def setUp(self):
    super().setUp()
    self.mock_check_issue_log_entry = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.logs_gs.CheckIssueLogEntry',
            autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(generalized_steps.GceLogCheck, 'add_child'))

  def test_gce_log_check_runs(self):
    self.params['filter_str'] = 'test-filter'
    step = generalized_steps.GceLogCheck()
    step.execute()
    self.mock_check_issue_log_entry.assert_called_once_with(
        project_id='test-project',
        filter_str='test-filter',
        issue_pattern=[],
        template='logging::gce_log',
        resource_name='resource NA')
    self.mock_add_child.assert_called_once()

  def test_gce_log_check_with_issue_pattern(self):
    self.params['filter_str'] = 'test-filter'
    self.params['issue_pattern'] = 'pattern1;;pattern2'
    step = generalized_steps.GceLogCheck()
    step.execute()
    self.mock_check_issue_log_entry.assert_called_once_with(
        project_id='test-project',
        filter_str='test-filter',
        issue_pattern=['pattern1', 'pattern2'],
        template='logging::gce_log',
        resource_name='resource NA')
    self.mock_add_child.assert_called_once()

  def test_gce_log_check_with_ref_filter(self):
    self.params['filter_str'] = 'ref:OOM_PATTERNS'
    step = generalized_steps.GceLogCheck()
    step.execute()
    self.mock_check_issue_log_entry.assert_called_once_with(
        project_id='test-project',
        filter_str=constants.OOM_PATTERNS,
        issue_pattern=[],
        template='logging::gce_log',
        resource_name='resource NA')
    self.mock_add_child.assert_called_once()

  def test_gce_log_check_missing_project_id(self):
    del self.params[flags.PROJECT_ID]
    step = generalized_steps.GceLogCheck()
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      step.execute()

  def test_gce_log_check_missing_filter_str(self):
    self.params['filter_str'] = None
    step = generalized_steps.GceLogCheck()
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      step.execute()


class VmHasOpsAgentTest(GceStepTestBase):
  """Test VmHasOpsAgent step."""

  def setUp(self):
    super().setUp()
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))

  def test_logging_agent_ok(self):
    step = generalized_steps.VmHasOpsAgent()
    step.check_metrics = False
    self.mock_logs_realtime_query.return_value = [{'log': 'data'}]
    step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_monitoring_query.assert_not_called()
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_logging_agent_failed(self):
    step = generalized_steps.VmHasOpsAgent()
    step.check_metrics = False
    self.mock_logs_realtime_query.return_value = []
    step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_monitoring_query.assert_not_called()
    self.mock_op_add_failed.assert_called_once()
    self.mock_op_add_ok.assert_not_called()

  def test_metrics_agent_ok(self):
    step = generalized_steps.VmHasOpsAgent()
    step.check_logging = False
    self.mock_monitoring_query.return_value = {
        'some_id': {
            'labels': {
                'metric.version': 'google-cloud-ops-agent-metrics-1'
            }
        }
    }
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_logs_realtime_query.assert_not_called()
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_metrics_agent_failed(self):
    step = generalized_steps.VmHasOpsAgent()
    step.check_logging = False
    self.mock_monitoring_query.return_value = {}
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_logs_realtime_query.assert_not_called()
    self.mock_op_add_failed.assert_called_once()
    self.mock_op_add_ok.assert_not_called()


class VmLifecycleStateTest(GceStepTestBase):
  """Test VmLifecycleState step."""

  def test_terminated_state_failed(self):
    step = generalized_steps.VmLifecycleState()
    step.expected_lifecycle_status = 'RUNNING'
    self.mock_instance.status = 'TERMINATED'
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_running_state_ok(self):
    step = generalized_steps.VmLifecycleState()
    step.expected_lifecycle_status = 'RUNNING'
    self.mock_instance.status = 'RUNNING'
    step.execute()
    self.mock_op_add_ok.assert_called_once()


class GceIamPolicyCheckTest(GceStepTestBase):
  """Test GceIamPolicyCheck step."""

  def setUp(self):
    super().setUp()
    self.mock_iam_policy_check = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.iam_gs.IamPolicyCheck',
            autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(generalized_steps.GceIamPolicyCheck, 'add_child'))

  def test_gce_iam_policy_check_runs_with_roles(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['roles'] = 'roles/viewer'
    step = generalized_steps.GceIamPolicyCheck()
    step.execute()
    self.mock_iam_policy_check.assert_called_once_with(
        project='test-project',
        principal='user:test@example.com',
        roles={'roles/viewer'},
        permissions=None,
        require_all=False)
    self.mock_add_child.assert_called_once()

  def test_gce_iam_policy_check_runs_with_permissions(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['permissions'] = 'compute.instances.get'
    step = generalized_steps.GceIamPolicyCheck()
    step.execute()
    self.mock_iam_policy_check.assert_called_once_with(
        project='test-project',
        principal='user:test@example.com',
        roles=None,
        permissions={'compute.instances.get'},
        require_all=False)
    self.mock_add_child.assert_called_once()

  def test_gce_iam_policy_check_with_ref_roles(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['roles'] = 'ref:DUMMY_ROLE'
    constants.DUMMY_ROLE = 'roles/dummy'
    step = generalized_steps.GceIamPolicyCheck()
    step.execute()
    self.mock_iam_policy_check.assert_called_once_with(
        project='test-project',
        principal='user:test@example.com',
        roles={'roles/dummy'},
        permissions=None,
        require_all=False)
    self.mock_add_child.assert_called_once()
    del constants.DUMMY_ROLE

  def test_gce_iam_policy_check_missing_project_id(self):
    del self.params[flags.PROJECT_ID]
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    self.params['roles'] = 'roles/viewer'
    step = generalized_steps.GceIamPolicyCheck()
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      step.execute()

  def test_gce_iam_policy_check_missing_principal(self):
    self.params['roles'] = 'roles/viewer'
    step = generalized_steps.GceIamPolicyCheck()
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      step.execute()

  def test_gce_iam_policy_check_missing_roles_and_permissions(self):
    self.params[iam_flags.PRINCIPAL] = 'user:test@example.com'
    step = generalized_steps.GceIamPolicyCheck()
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      step.execute()


class MigAutoscalingPolicyCheckTest(GceStepTestBase):
  """Test MigAutoscalingPolicyCheck step."""

  def setUp(self):
    super().setUp()
    self.mock_mig = mock.Mock()
    self.mock_mig.name = 'test-mig'
    self.mock_mig.zone = 'us-central1-a'
    self.mock_mig.region = None
    self.mock_mig.get = mock.Mock(return_value=None)
    self.mock_instance.created_by_mig = True
    self.mock_instance.mig = self.mock_mig
    self.mock_get_igm = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance_group_manager',
                   return_value=self.mock_mig))
    self.mock_get_rigm = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_region_instance_group_manager',
                   return_value=self.mock_mig))
    self.mock_autoscaler = mock.Mock()
    self.mock_autoscaler.get = mock.Mock(return_value=None)
    self.mock_get_autoscaler = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_autoscaler',
                   return_value=self.mock_autoscaler))
    self.mock_get_region_autoscaler = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_region_autoscaler',
                   return_value=self.mock_autoscaler))

  def test_check_policy_by_instance_ok(self):
    self.params.update({
        'property_path': 'some_property',
        'expected_value': 'some_value',
    })
    self.mock_mig.get.return_value = 'some_value'
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_mig.get.assert_called_once_with('some_property', default=None)
    self.mock_op_add_ok.assert_called_once()

  def test_check_policy_by_mig_name_fail(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        flags.MIG_NAME: 'test-mig',
        flags.LOCATION: 'us-central1-a',
        'property_path': 'some_property',
        'expected_value': 'other_value',
    })
    self.mock_mig.get.return_value = 'some_value'
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_get_igm.assert_called_once()
    self.mock_mig.get.assert_called_once_with('some_property', default=None)
    self.mock_op_add_failed.assert_called_once()

  def test_check_autoscaler_policy_ok(self):
    self.params.update({
        'property_path': 'autoscalingPolicy.mode',
        'expected_value': 'ON',
    })
    self.mock_autoscaler.get.return_value = 'ON'
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_get_autoscaler.assert_called_once()
    self.mock_autoscaler.get.assert_called_once_with('autoscalingPolicy.mode',
                                                     default=None)
    self.mock_op_add_ok.assert_called_once()

  def test_instance_not_in_mig(self):
    self.mock_instance.created_by_mig = False
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_mig_not_found_instance(self):
    self.mock_gce_get_instance.side_effect = apiclient.errors.HttpError(
        mock.Mock(status=404), b'not found')
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_mig_not_found_mig_name(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        flags.MIG_NAME: 'test-mig',
        flags.LOCATION: 'us-central1-a',
    })
    self.mock_get_igm.side_effect = apiclient.errors.HttpError(
        mock.Mock(status=404), b'not found')
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_check_regional_mig_policy_ok(self):
    self.params.update({
        flags.INSTANCE_NAME: None,
        flags.ZONE: None,
        flags.MIG_NAME: 'test-regional-mig',
        flags.LOCATION: 'us-central1',
        'property_path': 'some_property',
        'expected_value': 'some_value',
    })
    self.mock_mig.zone = None
    self.mock_mig.region = 'us-central1'
    self.mock_mig.get.return_value = 'some_value'
    self.mock_get_rigm.return_value = self.mock_mig
    step = generalized_steps.MigAutoscalingPolicyCheck()
    step.execute()
    self.mock_get_rigm.assert_called_once()
    self.mock_mig.get.assert_called_once_with('some_property', default=None)
    self.mock_op_add_ok.assert_called_once()
