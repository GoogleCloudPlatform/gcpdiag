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
"""Test class for gce/VmCreation"""

import datetime
import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.queries import apis_stub
from gcpdiag.runbook import gce, models, op, snapshot_test_base
from gcpdiag.runbook.crm import generalized_steps as crm_gs
from gcpdiag.runbook.gce import flags, vm_creation


class Test(snapshot_test_base.RulesSnapshotTestBase):
  """Snapshot tests for VM creation runbook."""
  rule_pkg = gce
  runbook_name = 'gce/vm-creation'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce6-aaaa',
      'instance_name': 'existing-instance',
      'zone': 'us-central1-c'
  }, {
      'project_id': 'gcpdiag-gce6-aaaa',
      'instance_name': 'non-existing-gpu-instance',
      'zone': 'us-central1-c'
  }]


class VmCreationUnitTests(unittest.TestCase):
  """Unit tests for VmCreation to cover lines not reached by snapshots."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(interface=self.mock_interface)
    self.operator.run_id = 'test-run'
    self.params = {
        flags.PROJECT_ID: 'gcpdiag-gce6-aaaa',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.END_TIME: datetime.datetime(2025, 1, 1),
        'start_time': datetime.datetime(2025, 1, 1),
    }
    self.operator.parameters = self.params
    self.operator.messages = models.Messages()
    self.operator.messages.update({
        'FAILURE_REASON': 'Reason {error_message}',
        'FAILURE_REMEDIATION': 'Remedy',
        'FAILURE_REASON_ALT1': 'Quota Reason {error_message}',
        'FAILURE_REMEDIATION_ALT1': 'Quota Remedy',
        'FAILURE_REASON_ALT2': 'Forbidden Reason {error_message}',
        'FAILURE_REMEDIATION_ALT2': 'Forbidden Remedy',
    })
    self.op_context = self.enterContext(op.operator_context(self.operator))

  def _get_base_entry(self):
    """Returns a baseline log entry structure to satisfy initial get_path calls."""
    return {
        'protoPayload': {
            'status': {
                'message': ''
            },
            'response': {
                'error': {
                    'errors': [{
                        'message': '',
                        'reason': ''
                    }]
                }
            }
        }
    }

  def test_build_tree_logic_zone_separation_true(self):
    self.params[flags.CHECK_ZONE_SEPARATION_POLICY] = True
    runbook_instance = vm_creation.VmCreation()
    runbook_instance.build_tree()
    step_types = [type(s) for s in runbook_instance.start.steps]
    self.assertIn(crm_gs.OrgPolicyCheck, step_types)

  def test_build_tree_logic_zone_separation_false(self):
    self.params[flags.CHECK_ZONE_SEPARATION_POLICY] = False
    runbook_instance = vm_creation.VmCreation()
    runbook_instance.build_tree()
    step_types = [type(s) for s in runbook_instance.start.steps]
    self.assertNotIn(crm_gs.OrgPolicyCheck, step_types)

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_execute_quota_exceeded(self, mock_query):
    entry = self._get_base_entry()
    entry['protoPayload']['status'] = {
        'message': 'QUOTA_EXCEEDED',
        'details': {
            'quotaExceeded': {
                'metricName': 'CPUS',
                'limit': 10,
                'limitName': 'CPUS-limit'
            }
        }
    }
    mock_query.return_value = [entry]
    step = vm_creation.InvestigateVmCreationLogFailure()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_execute_already_exists(self, mock_query):
    entry = self._get_base_entry()
    entry['protoPayload']['response']['error']['errors'][0] = {
        'reason': 'alreadyExists',
        'message': 'Instance exists'
    }
    mock_query.return_value = [entry]
    step = vm_creation.InvestigateVmCreationLogFailure()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_execute_forbidden(self, mock_query):
    entry = self._get_base_entry()
    entry['protoPayload']['response']['error']['errors'][0] = {
        'reason': 'forbidden',
        'message': 'Permission denied'
    }
    mock_query.return_value = [entry]
    step = vm_creation.InvestigateVmCreationLogFailure()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_failed.assert_called_once()

  @mock.patch('gcpdiag.queries.logs.realtime_query')
  def test_execute_no_logs(self, mock_query):
    mock_query.return_value = []
    step = vm_creation.InvestigateVmCreationLogFailure()
    self.operator.set_step(step)
    step.execute()
    self.mock_interface.add_failed.assert_not_called()
