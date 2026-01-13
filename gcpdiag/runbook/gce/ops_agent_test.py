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
"""Test class for gce/OpsAgent."""

import datetime
import unittest
from unittest import mock

import googleapiclient
import httplib2

from gcpdiag import config
from gcpdiag.queries import apis_stub, crm
from gcpdiag.queries import gce as queries_gce
from gcpdiag.runbook import gce, op, snapshot_test_base
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.gce import generalized_steps as gce_gs
from gcpdiag.runbook.gce import ops_agent
from gcpdiag.runbook.gcp import generalized_steps as gcp_gs
from gcpdiag.runbook.iam import generalized_steps as iam_gs


class MockMessage:
  """Mock messages for testing.

  Simply returns the key to verify template usage.
  """

  def get_msg(self, key, **kwargs):
    return f'{key}: {kwargs}'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce
  runbook_name = 'gce/ops-agent'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce3-aaaa',
      'instance_name': 'faulty-opsagent',
      'zone': 'europe-west2-a'
  }, {
      'project_id': 'gcpdiag-gce3-aaaa',
      'instance_name': 'faulty-opsagent-no-sa',
      'zone': 'europe-west2-a'
  }, {
      'project_id': 'gcpdiag-gce3-aaaa',
      'instance_name': 'working-opsagent',
      'zone': 'europe-west2-a'
  }]


class OpsAgentUnitTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    config.init({'auto': False, 'interface': 'cli'})
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()

    self.operator.parameters = {
        flags.PROJECT_ID: 'gcpdiag-gce3-aaaa',
        flags.ZONE: 'europe-west2-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.INSTANCE_ID: '1234',
        ops_agent.GAC_SERVICE_ACCOUNT: None,
        ops_agent.CHECK_LOGGING: True,
        ops_agent.CHECK_MONITORING: True,
        ops_agent.CHECK_SERIAL_PORT_LOGGING: True,
        flags.SERVICE_ACCOUNT: 'test@system.gserviceaccount.com',
        flags.START_TIME: datetime.datetime(2024, 1, 1),
        flags.END_TIME: datetime.datetime(2024, 1, 2),
    }
    self.op_context = self.enterContext(op.operator_context(self.operator))

    self.mock_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))
    self.mock_iam_get_sa_list = self.enterContext(
        mock.patch('gcpdiag.queries.iam.get_service_account_list'))
    self.mock_logs_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))

    self.project = mock.Mock(spec=crm.Project)
    self.project.id = 'gcpdiag-gce3-aaaa'
    self.instance = mock.Mock(spec=queries_gce.Instance)
    self.instance.name = 'test-instance'
    self.instance.id = '1234'
    self.instance.service_account = 'test@system.gserviceaccount.com'
    self.instance.full_path = (
        'projects/gcpdiag-gce3-aaaa/zones/europe-west2-a/instances/test-instance'
    )
    self.mock_get_project.return_value = self.project
    self.mock_get_instance.return_value = self.instance

  def test_start_step_instance_not_found(self):
    self.mock_get_instance.side_effect = googleapiclient.errors.HttpError(
        httplib2.Response({'status': 404}), b'not found')
    step = ops_agent.OpsAgentStart()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_start_step_instance_found(self):
    self.operator.parameters[flags.INSTANCE_ID] = None
    step = ops_agent.OpsAgentStart()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_skipped.assert_not_called()
    self.assertEqual(self.operator.parameters[flags.INSTANCE_ID], '1234')
    self.assertEqual(self.operator.parameters[flags.INSTANCE_NAME],
                     'test-instance')

  def test_vm_has_sa_no_gac_no_instance_sa(self):
    self.instance.service_account = None
    step = ops_agent.VmHasAServiceAccount()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_vm_has_sa_no_gac_with_instance_sa(self):
    self.instance.service_account = 'test@iam.gserviceaccount.com'
    step = ops_agent.VmHasAServiceAccount()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.assertEqual(self.operator.parameters[flags.SERVICE_ACCOUNT],
                     'test@iam.gserviceaccount.com')

  def test_vm_has_sa_gac_found(self):
    self.operator.parameters[
        ops_agent.
        GAC_SERVICE_ACCOUNT] = 'gac-sa@project.iam.gserviceaccount.com'
    sa = mock.Mock()
    sa.email = 'gac-sa@project.iam.gserviceaccount.com'
    self.mock_iam_get_sa_list.return_value = [sa]
    step = ops_agent.VmHasAServiceAccount()
    self.operator.set_step(step)
    step.execute()
    self.mock_iam_get_sa_list.assert_called_with('gcpdiag-gce3-aaaa')
    self.mock_interface.add_ok.assert_called_once()
    self.assertEqual(self.operator.parameters[flags.SERVICE_ACCOUNT],
                     'gac-sa@project.iam.gserviceaccount.com')

  def test_vm_has_sa_gac_not_found(self):
    self.operator.parameters[
        ops_agent.
        GAC_SERVICE_ACCOUNT] = 'gac-sa@project.iam.gserviceaccount.com'
    self.mock_iam_get_sa_list.return_value = []
    step = ops_agent.VmHasAServiceAccount()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_not_called()

  def test_investigate_logging_monitoring_all_enabled(self):
    step = ops_agent.InvestigateLoggingMonitoring()
    self.operator.set_step(step)
    step.execute()
    self.assertEqual(len(step.steps), 2)
    self.assertIsInstance(step.steps[0], gcp_gs.ServiceApiStatusCheck)
    self.assertEqual(step.steps[0].api_name, 'logging')
    self.assertIsInstance(step.steps[1], gcp_gs.ServiceApiStatusCheck)
    self.assertEqual(step.steps[1].api_name, 'monitoring')

    logging_api_step = step.steps[0]
    self.assertEqual(len(logging_api_step.steps), 3)
    self.assertIsInstance(logging_api_step.steps[0], iam_gs.IamPolicyCheck)
    self.assertIsInstance(logging_api_step.steps[1], gce_gs.VmScope)
    self.assertIsInstance(logging_api_step.steps[2],
                          ops_agent.CheckSerialPortLogging)
    self.assertIsInstance(logging_api_step.steps[1].steps[0],
                          gce_gs.VmHasOpsAgent)

    monitoring_api_step = step.steps[1]
    self.assertEqual(len(monitoring_api_step.steps), 2)
    self.assertIsInstance(monitoring_api_step.steps[0], iam_gs.IamPolicyCheck)
    self.assertIsInstance(monitoring_api_step.steps[1], gce_gs.VmScope)
    self.assertIsInstance(monitoring_api_step.steps[1].steps[0],
                          gce_gs.VmHasOpsAgent)

  def test_investigate_logging_disabled(self):
    self.operator.parameters[ops_agent.CHECK_LOGGING] = False
    step = ops_agent.InvestigateLoggingMonitoring()
    self.operator.set_step(step)
    step.execute()
    self.assertEqual(len(step.steps), 1)
    self.assertEqual(step.steps[0].api_name, 'monitoring')

  def test_investigate_monitoring_disabled(self):
    self.operator.parameters[ops_agent.CHECK_MONITORING] = False
    step = ops_agent.InvestigateLoggingMonitoring()
    self.operator.set_step(step)
    step.execute()
    self.assertEqual(len(step.steps), 1)
    self.assertEqual(step.steps[0].api_name, 'logging')

  def test_investigate_no_serial_port_logging(self):
    self.operator.parameters[ops_agent.CHECK_SERIAL_PORT_LOGGING] = False
    step = ops_agent.InvestigateLoggingMonitoring()
    self.operator.set_step(step)
    step.execute()
    self.assertEqual(len(step.steps), 2)
    logging_api_step = step.steps[0]
    self.assertEqual(len(logging_api_step.steps), 2)
    self.assertIsInstance(logging_api_step.steps[0], iam_gs.IamPolicyCheck)
    self.assertIsInstance(logging_api_step.steps[1], gce_gs.VmScope)

  def test_check_serial_port_logging(self):
    step = ops_agent.CheckSerialPortLogging()
    self.operator.set_step(step)
    step.execute()
    self.assertEqual(len(step.steps), 2)
    self.assertIsInstance(step.steps[0], crm_gs.OrgPolicyCheck)
    self.assertIsInstance(step.steps[1], gce_gs.VmMetadataCheck)

  def test_end_step_serial_logs_found(self):
    self.mock_logs_query.return_value = [{'some': 'log'}]
    self.mock_monitoring_query.return_value = {}
    step = ops_agent.OpsAgentEnd()
    self.operator.set_step(step)
    step.execute()
    self.mock_logs_query.assert_called_once()
    self.mock_interface.info.assert_called_with(
        'There are new logs indicating ops agent is exporting serial logs',
        step_type='INFO')

  def test_end_step_metrics_found(self):
    self.mock_logs_query.return_value = []
    self.mock_monitoring_query.return_value = {
        'entry1': {
            'labels': {
                'metric.version': 'google-cloud-ops-agent-metrics-1'
            }
        }
    }
    step = ops_agent.OpsAgentEnd()
    self.operator.set_step(step)
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_interface.info.assert_called_with(
        'There is metrics data indicating ops agent is exporting metrics'
        ' correctly!',
        step_type='INFO')

  def test_end_step_no_logs_metrics_prompt_no(self):
    self.mock_logs_query.return_value = []
    self.mock_monitoring_query.return_value = {}
    with mock.patch('gcpdiag.runbook.op.prompt',
                    return_value=op.NO) as mock_prompt:
      step = ops_agent.OpsAgentEnd()
      self.operator.set_step(step)
      step.execute()
      mock_prompt.assert_called_once()
      self.mock_interface.info.assert_called_with(message=op.END_MESSAGE,
                                                  step_type='INFO')

  def test_end_step_no_logs_metrics_prompt_yes(self):
    self.mock_logs_query.return_value = []
    self.mock_monitoring_query.return_value = {}
    with mock.patch('gcpdiag.runbook.op.prompt', return_value=op.YES):
      step = ops_agent.OpsAgentEnd()
      self.operator.set_step(step)
      step.execute()
      self.mock_interface.info.assert_not_called()

  def test_end_step_no_serial_check(self):
    self.operator.parameters[ops_agent.CHECK_SERIAL_PORT_LOGGING] = False
    self.mock_monitoring_query.return_value = {}
    step = ops_agent.OpsAgentEnd()
    self.operator.set_step(step)
    step.execute()
    self.mock_logs_query.assert_not_called()

  def test_ops_agent_tree_structure(self):
    """Tests that the diagnostic tree is built with correct step relationships."""
    tree = ops_agent.OpsAgent()
    tree.add_start = mock.Mock()
    tree.add_step = mock.Mock()
    tree.add_end = mock.Mock()
    with op.operator_context(self.operator):
      tree.build_tree()

    tree.add_start.assert_called_once()
    start_arg = tree.add_start.call_args[0][0]
    self.assertIsInstance(start_arg, ops_agent.OpsAgentStart)

    tree.add_end.assert_called_once()
    end_arg = tree.add_end.call_args[0][0]
    self.assertIsInstance(end_arg, ops_agent.OpsAgentEnd)

    self.assertEqual(tree.add_step.call_count, 3)

    calls = tree.add_step.call_args_list

    def assert_relationship(parent_type, child_type):
      found = False
      for call in calls:
        args, kwargs = call
        p = kwargs.get('parent') if 'parent' in kwargs else args[0]
        c = kwargs.get('child') if 'child' in kwargs else args[1]

        if isinstance(p, parent_type) and isinstance(c, child_type):
          found = True
          break
      self.assertTrue(
          found,
          f'Relationship {parent_type.__name__} -> {child_type.__name__} not'
          ' found',
      )

    with op.operator_context(self.operator):
      assert_relationship(ops_agent.OpsAgentStart,
                          ops_agent.VmHasAServiceAccount)
      assert_relationship(ops_agent.VmHasAServiceAccount,
                          iam_gs.VmHasAnActiveServiceAccount)
      assert_relationship(ops_agent.VmHasAServiceAccount,
                          ops_agent.InvestigateLoggingMonitoring)

  def test_vm_has_sa_failure_condition_no_gac_no_sa(self):
    """Tests the failure path when no GAC and no Instance SA are present."""
    self.instance.service_account = None

    step = ops_agent.VmHasAServiceAccount()
    self.operator.set_step(step)
    step.execute()

    self.mock_interface.add_failed.assert_called_once()

    kwargs = self.mock_interface.add_failed.call_args[1]
    self.assertEqual(kwargs['resource'], self.instance)
    self.assertIn('reason', kwargs)
    self.assertIn('remediation', kwargs)

    self.assertIn(self.instance.full_path, kwargs['reason'])
