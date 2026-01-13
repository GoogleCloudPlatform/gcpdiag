# Copyright 2022 Google LLC
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
"""Generalize rule snapshot testing."""

import unittest
from unittest import mock

from dateutil import parser

from gcpdiag import config
from gcpdiag.queries import apis_stub, crm, gce
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import gce as gce_runbook
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.gce import flags, ssh


class MockMessage:
  """Mock messages for testing.

  Simply returns the key to verify template usage.
  """

  def get_msg(self, key, **kwargs):
    return f'{key}: {kwargs}'


class SshStepTestBase(unittest.TestCase):
  """Base class for SSH runbook tests."""

  def setUp(self):
    super().setUp()
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    self.params = {
        flags.PROJECT_ID: 'gcpdiag-gce-faultyssh-runbook',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.START_TIME: parser.parse('2025-01-23 23:30:39.144959+00:00'),
        flags.END_TIME: parser.parse('2025-01-23 13:30:39.144959+00:00')
    }
    self.operator.parameters = self.params
    self.mock_instance = mock.Mock(spec=gce.Instance)
    self.mock_instance.is_public_machine.return_value = False
    self.mock_instance.is_windows_machine.return_value = False
    self.mock_instance.get_metadata.return_value = ''
    self.mock_gce_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance',
                   return_value=self.mock_instance))
    self.mock_ensure_instance_resolved = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.util.ensure_instance_resolved'))
    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.id = self.params[flags.PROJECT_ID]
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project',
                   return_value=self.mock_project))


class SshTreeTest(SshStepTestBase):
  """Test Ssh DiagnosticTree methods."""

  def test_legacy_parameter_handler(self):
    """Verify deprecated parameter mapping."""
    params = {
        flags.NAME: 'legacy-name',
        flags.ID: 12345,
        flags.LOCAL_USER: 'legacy-user',
        flags.TUNNEL_THROUGH_IAP: True,
        flags.CHECK_OS_LOGIN: True,
        ssh.CHECK_SSH_IN_BROWSER: True,
        flags.PROTOCOL_TYPE: 'tcp'
    }
    tree = ssh.Ssh()
    tree.legacy_parameter_handler(params)

    self.assertEqual(params[flags.INSTANCE_NAME], 'legacy-name')
    self.assertEqual(params[flags.INSTANCE_ID], 12345)
    self.assertEqual(params[flags.POSIX_USER], 'legacy-user')
    self.assertEqual(params[flags.PROXY], ssh.IAP)
    self.assertEqual(params[flags.ACCESS_METHOD], ssh.OSLOGIN)
    self.assertEqual(params[flags.CLIENT], ssh.SSH_IN_BROWSER)
    self.assertNotIn(flags.PROTOCOL_TYPE, params)

  def test_build_tree(self):
    """Verify tree structure assembly."""
    self.operator.parameters[flags.PRINCIPAL] = 'user:test@example.com'
    self.operator.parameters[ssh.CLIENT] = ssh.SSH_IN_BROWSER

    tree = ssh.Ssh()
    with op.operator_context(self.operator):
      tree.build_tree()
    self.assertIsInstance(tree.start, ssh.SshStart)

    child_names = [c.__class__.__name__ for c in tree.start.steps]
    self.assertIn('VmLifecycleState', child_names)
    self.assertIn('GcpSshPermissions', child_names)
    self.assertIn('GceFirewallAllowsSsh', child_names)
    self.assertIn('SshInBrowserCheck', child_names)


class SshStartTest(SshStepTestBase):
  """Test SshStart."""

  def setUp(self):
    super().setUp()
    self.mock_iam_get_project_policy = self.enterContext(
        mock.patch('gcpdiag.queries.iam.get_project_policy'))

  def test_ssh_start_runs(self):
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_crm_get_project.assert_called_once()
    self.mock_ensure_instance_resolved.assert_called_once()
    self.mock_gce_get_instance.assert_called_once()

  def test_ssh_start_principal_handling(self):
    self.operator.parameters[flags.PRINCIPAL] = 'test@example.com'
    self.mock_instance.is_public_machine.return_value = False
    mock_policy = mock.Mock()
    mock_policy.get_member_type.return_value = 'user'
    self.mock_iam_get_project_policy.return_value = mock_policy
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.operator.parameters[flags.PRINCIPAL],
                     'user:test@example.com')
    self.mock_interface.info.assert_any_call(
        'GCP permissions related to SSH will be verified for:'
        ' user:test@example.com',
        step_type='INFO')

  def test_ssh_start_iap_proxy(self):
    self.operator.parameters[flags.PROXY] = ssh.IAP
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.operator.parameters[flags.SRC_IP],
                     gce_runbook.constants.IAP_FW_VIP)
    self.mock_interface.info.assert_any_call(
        'Source IP to be used for SSH connectivity test: '
        '35.235.240.0/20',
        step_type='INFO')

  def test_ssh_start_instance_not_found(self):
    self.mock_ensure_instance_resolved.side_effect = (
        runbook_exceptions.FailedStepError('instance not found'))
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_ssh_start_public_vm_no_proxy(self):
    self.mock_instance.is_public_machine.return_value = True
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(
        self.operator.parameters[flags.SRC_IP],
        gce_runbook.constants.UNSPECIFIED_ADDRESS,
    )
    self.mock_interface.info.assert_any_call(
        'No proxy specified. Setting source IP range to: 0.0.0.0/0',
        step_type='INFO',
    )

  def test_ssh_start_jumphost_proxy(self):
    self.operator.parameters[flags.PROXY] = ssh.JUMPHOST
    self.operator.parameters[flags.SRC_IP] = '10.0.0.1'
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Source IP to be used for SSH connectivity test: 10.0.0.1',
        step_type='INFO',
    )

  def test_ssh_start_oslogin_message(self):
    self.operator.parameters[ssh.ACCESS_METHOD] = ssh.OSLOGIN
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Access method to investigate: OS login'
        ' https://cloud.google.com/compute/docs/oslogin',
        step_type='INFO')

  def test_ssh_start_ssh_key_in_metadata_message(self):
    self.operator.parameters[ssh.ACCESS_METHOD] = ssh.SSH_KEY_IN_METADATA
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Access method to investigate: SSH keys in metadata '
        'https://cloud.google.com/compute/docs/instances/access-overview#ssh-access',
        step_type='INFO')

  def test_ssh_start_gcloud_client_message(self):
    self.operator.parameters[ssh.CLIENT] = ssh.GCLOUD
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Investigating components required to use gcloud compute ssh',
        step_type='INFO',
    )

  def test_ssh_start_oslogin_2fa_message(self):
    self.operator.parameters[ssh.MFA] = ssh.OSLOGIN_2FA
    step = ssh.SshStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_any_call(
        'Multifactor authentication to investigate: OS Login 2FA '
        'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#byb',
        step_type='INFO',
    )


class VmGuestOsTypeTest(SshStepTestBase):
  """Test VmGuestOsType."""

  def setUp(self):
    super().setUp()
    self.mock_linux_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.LinuxGuestOsChecks', autospec=True))
    self.mock_windows_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.WindowsGuestOsChecks',
                   autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.VmGuestOsType, 'add_child'))

  def test_linux_os(self):
    self.mock_instance.is_windows_machine.return_value = False
    step = ssh.VmGuestOsType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(
        self.mock_add_child.call_args[0][0].__class__.__name__,
        'LinuxGuestOsChecks',
    )

  def test_windows_os(self):
    self.mock_instance.is_windows_machine.return_value = True
    step = ssh.VmGuestOsType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(
        self.mock_add_child.call_args[0][0].__class__.__name__,
        'WindowsGuestOsChecks',
    )

  def test_instance_not_found(self):
    self.mock_ensure_instance_resolved.side_effect = (
        runbook_exceptions.FailedStepError('instance not found'))
    step = ssh.VmGuestOsType()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.mock_add_child.assert_not_called()


class SshEndTest(SshStepTestBase):
  """Test SshEnd."""

  def setUp(self):
    super().setUp()
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))
    self.enterContext(mock.patch('gcpdiag.config.get',
                                 return_value=True))  # INTERACTIVE_MODE

  def test_ssh_end_no_interactive(self):
    self.enterContext(mock.patch('gcpdiag.config.get', return_value=False))
    self.mock_op_prompt.return_value = op.NO
    step = ssh.SshEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_interface.info.assert_called_once_with(message=op.END_MESSAGE,
                                                     step_type='INFO')

  def test_ssh_end_yes_interactive(self):
    self.mock_op_prompt.return_value = op.YES
    step = ssh.SshEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_not_called()


class SshInBrowserCheckTest(SshStepTestBase):
  """Test SshInBrowserCheck."""

  def setUp(self):
    super().setUp()
    self.mock_org_policy_check = self.enterContext(
        mock.patch('gcpdiag.runbook.crm.generalized_steps.OrgPolicyCheck',
                   autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.SshInBrowserCheck, 'add_child'))

  def test_ssh_in_browser_check(self):
    step = ssh.SshInBrowserCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(self.mock_add_child.call_args[0][0].__class__.__name__,
                     'OrgPolicyCheck')
    self.assertEqual(self.mock_add_child.call_args[0][0].constraint,
                     'constraints/compute.disableSshInBrowser')


class GcpSshPermissionsTest(SshStepTestBase):
  """Test GcpSshPermissions."""

  def setUp(self):
    super().setUp()
    self.mock_iam_policy_check = self.enterContext(
        mock.patch('gcpdiag.runbook.iam.generalized_steps.IamPolicyCheck'))
    self.mock_iam_policy_check.side_effect = mock.MagicMock
    self.mock_os_login_status_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.OsLoginStatusCheck', autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.GcpSshPermissions, 'add_child'))

  def test_base_permissions_checked(self):
    step = ssh.GcpSshPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_add_child.call_args_list[0][0][0].template,
                     'gcpdiag.runbook.gce::permissions::instances_get')
    self.assertEqual(
        self.mock_add_child.call_args_list[1][0][0].__class__.__name__,
        'OsLoginStatusCheck')

  def test_iap_permissions_checked(self):
    self.operator.parameters[flags.PROXY] = ssh.IAP
    step = ssh.GcpSshPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_add_child.call_args_list[-1][0][0].template,
                     'gcpdiag.runbook.gce::permissions::iap_role')

  def test_permissions_ssh_in_browser(self):
    """Cover line 353: Console view permission for browser client."""
    self.operator.parameters[ssh.CLIENT] = ssh.SSH_IN_BROWSER
    with op.operator_context(self.operator):
      step = ssh.GcpSshPermissions()
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(
        self.mock_add_child.call_args_list[0][0][0].template,
        'gcpdiag.runbook.gce::permissions::console_view_permission')


class OsLoginStatusCheckTest(SshStepTestBase):
  """Test OsLoginStatusCheck."""

  def setUp(self):
    super().setUp()
    self.mock_vm_metadata_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmMetadataCheck'))
    self.mock_vm_metadata_check.side_effect = mock.MagicMock

    self.mock_iam_policy_check = self.enterContext(
        mock.patch('gcpdiag.runbook.iam.generalized_steps.IamPolicyCheck'))
    self.mock_iam_policy_check.side_effect = mock.MagicMock

    self.mock_posix_user_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.PosixUserHasValidSshKeyCheck',
                   autospec=True))
    self.mock_duplicate_keys_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.VmDuplicateSshKeysCheck',
                   autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.OsLoginStatusCheck, 'add_child'))

  def test_os_login_path(self):
    self.operator.parameters[ssh.ACCESS_METHOD] = ssh.OSLOGIN
    step = ssh.OsLoginStatusCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()

    self.assertEqual(self.mock_add_child.call_count, 3)
    templates = [
        getattr(call[0][0], 'template', '')
        for call in self.mock_add_child.call_args_list
    ]
    self.assertIn('vm_metadata::os_login_enabled', templates)
    self.assertIn('gcpdiag.runbook.gce::permissions::has_os_login', templates)
    self.assertIn('gcpdiag.runbook.gce::permissions::sa_user_role', templates)

  def test_ssh_key_in_metadata_path(self):
    """Verify metadata based SSH path."""
    self.operator.parameters[ssh.ACCESS_METHOD] = ssh.SSH_KEY_IN_METADATA
    step = ssh.OsLoginStatusCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_add_child.call_count, 4)
    self.assertEqual(self.mock_add_child.call_args_list[0][0][0].template,
                     'gcpdiag.runbook.gce::permissions::can_set_metadata')
    self.assertEqual(self.mock_add_child.call_args_list[1][0][0].template,
                     'vm_metadata::no_os_login')
    self.assertEqual(
        self.mock_add_child.call_args_list[2][0][0].__class__.__name__,
        'PosixUserHasValidSshKeyCheck')
    self.assertEqual(
        self.mock_add_child.call_args_list[3][0][0].__class__.__name__,
        'VmDuplicateSshKeysCheck')


class PosixUserHasValidSshKeyCheckTest(SshStepTestBase):
  """Test PosixUserHasValidSshKeyCheck."""

  def setUp(self):
    super().setUp()
    self.mock_user_has_valid_ssh_key = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.util.user_has_valid_ssh_key'))
    self.operator.parameters[flags.POSIX_USER] = 'testuser'

  def test_valid_key_present(self):
    self.mock_instance.get_metadata.return_value = (
        'testuser:ssh-rsa AAA... testuser@host')
    self.mock_user_has_valid_ssh_key.return_value = True
    step = ssh.PosixUserHasValidSshKeyCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_no_valid_key(self):
    self.mock_instance.get_metadata.return_value = (
        'otheruser:ssh-rsa BBB... otheruser@host')
    self.mock_user_has_valid_ssh_key.return_value = False
    step = ssh.PosixUserHasValidSshKeyCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()


class VmDuplicateSshKeysCheckTest(SshStepTestBase):
  """Test VmDuplicateSshKeysCheck."""

  def test_no_ssh_keys(self):
    self.mock_instance.get_metadata.return_value = ''
    step = ssh.VmDuplicateSshKeysCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_duplicate_keys(self):
    ssh_keys = ('user1:ssh-rsa SAMEKEY... user1@host\n'
                'user2:ssh-rsa BBB... user2@host\n'
                'user3:ssh-rsa SAMEKEY... user3@host')
    self.mock_instance.get_metadata.return_value = ssh_keys
    step = ssh.VmDuplicateSshKeysCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_no_duplicate_keys(self):
    ssh_keys = ('user1:ssh-rsa KEY1... user1@host\n'
                'ssh-rsa KEY2... user2@host\n\n'
                'user3:ssh-rsa KEY3... user3@host')
    self.mock_instance.get_metadata.return_value = ssh_keys
    step = ssh.VmDuplicateSshKeysCheck()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_duplicate_keys_detection(self):
    """Cover duplicate blobs even with different prefixes/spacing."""
    ssh_keys = (
        'user1:ssh-rsa AAA... user1@host\n'
        'ssh-rsa AAA... user2@host\n'  # Duplicate blob
        '  \n'  # Empty line
        'user3: ssh-rsa BBB... user3@host\n'  # Space after colon
    )
    self.mock_instance.get_metadata.return_value = ssh_keys
    with op.operator_context(self.operator):
      step = ssh.VmDuplicateSshKeysCheck()
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn('AAA...',
                  self.mock_interface.add_failed.call_args[1]['reason'])


class GceFirewallAllowsSshTest(SshStepTestBase):
  """Test GceFirewallAllowsSsh."""

  def setUp(self):
    super().setUp()
    self.mock_vpc_connectivity_check = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.GceVpcConnectivityCheck',
            autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.GceFirewallAllowsSsh, 'add_child'))

  def test_iap_firewall_check(self):
    self.operator.parameters[flags.PROXY] = ssh.IAP
    self.operator.parameters[flags.SRC_IP] = gce_runbook.constants.IAP_FW_VIP
    step = ssh.GceFirewallAllowsSsh()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(
        self.mock_add_child.call_args[0][0].template,
        'vpc_connectivity::tti_ingress',
    )

  def test_public_vm_firewall_check(self):
    self.mock_instance.is_public_machine.return_value = True
    self.operator.parameters[flags.SRC_IP] = (
        gce_runbook.constants.UNSPECIFIED_ADDRESS)
    step = ssh.GceFirewallAllowsSsh()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(
        self.mock_add_child.call_args[0][0].template,
        'vpc_connectivity::default_ingress',
    )

  def test_custom_ip_firewall_check(self):
    """Verify custom source IP branch."""
    self.operator.parameters[flags.SRC_IP] = '10.0.0.1'
    self.operator.parameters[flags.PROXY] = None
    step = ssh.GceFirewallAllowsSsh()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(self.mock_add_child.call_args[0][0].template,
                     'vpc_connectivity::default_ingress')


class VmPerformanceChecksTest(SshStepTestBase):
  """Test VmPerformanceChecks."""

  def setUp(self):
    super().setUp()
    self.mock_hum = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.HighVmMemoryUtilization'))
    self.mock_hud = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.HighVmDiskUtilization'))
    self.mock_huc = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.generalized_steps.HighVmCpuUtilization'))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.VmPerformanceChecks, 'add_child'))

  def test_performance_checks_added(self):
    mem = self.mock_hum.return_value
    disk = self.mock_hud.return_value
    cpu = self.mock_huc.return_value
    step = ssh.VmPerformanceChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_add_child.assert_has_calls(
        [mock.call(child=mem),
         mock.call(child=disk),
         mock.call(child=cpu)])


class LinuxGuestOsChecksTest(SshStepTestBase):
  """Test LinuxGuestOsChecks."""

  def setUp(self):
    super().setUp()
    self.mock_vm_serial_logs_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmSerialLogsCheck'))
    self.mock_vm_serial_logs_check.side_effect = mock.MagicMock
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.LinuxGuestOsChecks, 'add_child'))

  def test_linux_checks_added(self):
    self.mock_vm_serial_logs_check.side_effect = [
        mock.MagicMock(), mock.MagicMock(),
        mock.MagicMock()
    ]
    step = ssh.LinuxGuestOsChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_add_child.call_count, 3)
    self.assertEqual(self.mock_add_child.call_args_list[0].args[0].template,
                     'vm_serial_log::kernel_panic')
    self.assertEqual(self.mock_add_child.call_args_list[1].args[0].template,
                     'vm_serial_log::sshd')
    self.assertEqual(self.mock_add_child.call_args_list[2].args[0].template,
                     'vm_serial_log::sshguard')


class WindowsGuestOsChecksTest(SshStepTestBase):
  """Test WindowsGuestOsChecks."""

  def setUp(self):
    super().setUp()
    self.mock_vm_metadata_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmMetadataCheck',
                   autospec=True))
    self.mock_vm_serial_logs_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmSerialLogsCheck',
                   autospec=True))
    self.mock_human_task = self.enterContext(
        mock.patch('gcpdiag.runbook.gcp.generalized_steps.HumanTask',
                   autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.WindowsGuestOsChecks, 'add_child'))

  def test_windows_checks_added(self):
    step = ssh.WindowsGuestOsChecks()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.mock_add_child.call_count, 3)
    self.assertEqual(self.mock_add_child.call_args_list[0].args[0].template,
                     'vm_metadata::windows_ssh_md')
    self.assertEqual(self.mock_add_child.call_args_list[1].args[0].template,
                     'vm_serial_log::windows_bootup')
    self.assertEqual(
        self.mock_add_child.call_args_list[2].args[0].__class__.__name__,
        'HumanTask')

  def test_windows_human_task_added(self):
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.WindowsGuestOsChecks, 'add_child'))
    with op.operator_context(self.operator):
      step = ssh.WindowsGuestOsChecks()
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(
        self.mock_add_child.call_args_list[2].args[0].__class__.__name__,
        'HumanTask')


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce_runbook
  runbook_name = 'gce/ssh'
  config.init({'auto': True, 'interface': 'cli'})

  rule_parameters = [{
      'project_id': 'gcpdiag-gce-faultyssh-runbook',
      'instance_name': 'faulty-linux-ssh',
      'zone': 'europe-west2-a',
      'principal': 'user:cannotssh@example.com',
      'proxy': 'iap',
      'access_method': 'oslogin',
      'start_time': '2025-01-23 23:30:39.144959+00:00',
      'end_time': '2025-01-23 13:30:39.144959+00:00'
  }, {
      'project_id':
          'gcpdiag-gce-faultyssh-runbook',
      'instance_name':
          'valid-linux-ssh',
      'zone':
          'europe-west2-a',
      'principal':
          'serviceAccount:canssh@gcpdiag-gce-faultyssh-runbook.iam.gserviceaccount.com',
      'proxy':
          'iap',
      'access_method':
          'oslogin',
      'start_time':
          '2025-01-23 23:30:39.144959+00:00',
      'end_time':
          '2025-01-23 13:30:39.144959+00:00'
  }, {
      'project_id': 'gcpdiag-gce-faultyssh-runbook',
      'instance_name': 'faulty-windows-ssh',
      'zone': 'europe-west2-a',
      'principal': 'user:cannot@example.com',
      'src_ip': '0.0.0.0',
      'proxy': 'iap',
      'access_method': 'oslogin',
      'posix_user': 'no_user',
      'start_time': '2025-01-23 23:30:39.144959+00:00',
      'end_time': '2025-01-23 13:30:39.144959+00:00'
  }]
