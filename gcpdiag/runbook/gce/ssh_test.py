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
""" Generalize rule snapshot testing """

from unittest import mock

from dateutil import parser

from gcpdiag import config
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook import gce as gce_runbook
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.gce import flags, ssh

# Import the base class from your generalized_steps_test file,
# assuming it's in the same directory or accessible.
from .generalized_steps_test import GceStepTestBase

# Refactored gcpdiag/runbook/gce/ssh_test.py


class SshStepTestBase(GceStepTestBase):
  """Base class for SSH runbook tests."""

  def setUp(self):
    super().setUp()
    self.op_get_values = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.START_TIME: parser.parse('2025-01-23 23:30:39.144959+00:00'),
        flags.END_TIME: parser.parse('2025-01-23 13:30:39.144959+00:00')
    }
    self.mock_op_get.side_effect = lambda key, d=None: self.op_get_values.get(
        key, d)
    self.params.update(self.op_get_values)
    self.mock_instance.is_public_machine.return_value = False
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))

    def mock_put(key, value):
      self.op_get_values[key] = value
      self.params[key] = value

    self.mock_op_put.side_effect = mock_put


class SshStartTest(SshStepTestBase):
  """Test SshStart."""

  def setUp(self):
    super().setUp()
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_iam_get_project_policy = self.enterContext(
        mock.patch('gcpdiag.queries.iam.get_project_policy'))
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))

  def test_ssh_start_runs(self):
    step = ssh.SshStart()
    step.execute()
    self.mock_crm_get_project.assert_called_once()
    self.mock_ensure_instance_resolved.assert_called_once()
    self.mock_gce_get_instance.assert_called_once()

  def test_ssh_start_principal_handling(self):
    self.op_get_values[flags.PRINCIPAL] = 'test@example.com'
    self.mock_instance.is_public_machine.return_value = False
    mock_policy = mock.Mock()
    mock_policy.get_member_type.return_value = 'user'
    self.mock_iam_get_project_policy.return_value = mock_policy
    step = ssh.SshStart()
    step.execute()
    self.mock_op_put.assert_called_with(flags.PRINCIPAL,
                                        'user:test@example.com')
    self.mock_op_info.assert_any_call(
        'GCP permissions related to SSH will be verified for: user:test@example.com'
    )

  def test_ssh_start_iap_proxy(self):
    self.op_get_values[flags.PROXY] = ssh.IAP
    step = ssh.SshStart()
    step.execute()
    self.mock_op_put.assert_called_with(flags.SRC_IP,
                                        gce_runbook.constants.IAP_FW_VIP)
    self.mock_op_info.assert_any_call(
        'Source IP to be used for SSH connectivity test: 35.235.240.0/20')

  def test_ssh_start_instance_not_found(self):
    self.mock_ensure_instance_resolved.side_effect = runbook_exceptions.FailedStepError(
        'instance not found')
    step = ssh.SshStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_ssh_start_public_vm_no_proxy(self):
    self.mock_instance.is_public_machine.return_value = True
    step = ssh.SshStart()
    step.execute()
    self.mock_op_put.assert_called_with(
        flags.SRC_IP, gce_runbook.constants.UNSPECIFIED_ADDRESS)
    self.mock_op_info.assert_any_call(
        'No proxy specified. Setting source IP range to: 0.0.0.0/0')

  def test_ssh_start_jumphost_proxy(self):
    self.op_get_values[flags.PROXY] = ssh.JUMPHOST
    self.op_get_values[flags.SRC_IP] = '10.0.0.1'
    step = ssh.SshStart()
    step.execute()
    self.mock_op_info.assert_any_call(
        'Source IP to be used for SSH connectivity test: 10.0.0.1')

  def test_ssh_start_oslogin_message(self):
    self.op_get_values[ssh.ACCESS_METHOD] = ssh.OSLOGIN
    step = ssh.SshStart()
    step.execute()
    self.mock_op_info.assert_any_call(
        'Access method to investigate: OS login https://cloud.google.com/compute/docs/oslogin'
    )

  def test_ssh_start_ssh_key_in_metadata_message(self):
    self.op_get_values[ssh.ACCESS_METHOD] = ssh.SSH_KEY_IN_METADATA
    step = ssh.SshStart()
    step.execute()
    self.mock_op_info.assert_any_call(
        'Access method to investigate: SSH keys in metadata '
        'https://cloud.google.com/compute/docs/instances/access-overview#ssh-access'
    )

  def test_ssh_start_gcloud_client_message(self):
    self.op_get_values[ssh.CLIENT] = ssh.GCLOUD
    step = ssh.SshStart()
    step.execute()
    self.mock_op_info.assert_any_call(
        'Investigating components required to use gcloud compute ssh')

  def test_ssh_start_oslogin_2fa_message(self):
    self.op_get_values[ssh.MFA] = ssh.OSLOGIN_2FA
    step = ssh.SshStart()
    step.execute()
    self.mock_op_info.assert_any_call(
        'Multifactor authentication to investigate: OS Login 2FA '
        'https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#byb')


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
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))

  def test_linux_os(self):
    self.mock_instance.is_windows_machine.return_value = False
    step = ssh.VmGuestOsType()
    step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(self.mock_add_child.call_args[0][0].__class__.__name__,
                     'LinuxGuestOsChecks')

  def test_windows_os(self):
    self.mock_instance.is_windows_machine.return_value = True
    step = ssh.VmGuestOsType()
    step.execute()
    self.mock_add_child.assert_called_once()
    self.assertEqual(self.mock_add_child.call_args[0][0].__class__.__name__,
                     'WindowsGuestOsChecks')

  def test_instance_not_found(self):
    self.mock_ensure_instance_resolved.side_effect = runbook_exceptions.FailedStepError(
        'instance not found')
    step = ssh.VmGuestOsType()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()
    self.mock_add_child.assert_not_called()


class SshEndTest(SshStepTestBase):
  """Test SshEnd."""

  def setUp(self):
    super().setUp()
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))
    self.enterContext(mock.patch('gcpdiag.config.get',
                                 return_value=True))  # INTERACTIVE_MODE

  def test_ssh_end_no_interactive(self):
    self.enterContext(mock.patch('gcpdiag.config.get', return_value=False))
    self.mock_op_prompt.return_value = op.NO
    step = ssh.SshEnd()
    step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_op_info.assert_called_once_with(message=op.END_MESSAGE)

  def test_ssh_end_yes_interactive(self):
    self.mock_op_prompt.return_value = op.YES
    step = ssh.SshEnd()
    step.execute()
    self.mock_op_info.assert_not_called()


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
        mock.patch('gcpdiag.runbook.iam.generalized_steps.IamPolicyCheck',
                   autospec=True))
    self.mock_os_login_status_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.OsLoginStatusCheck', autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.GcpSshPermissions, 'add_child'))

  def test_base_permissions_checked(self):
    step = ssh.GcpSshPermissions()
    step.execute()
    self.assertEqual(self.mock_add_child.call_args_list[0][0][0].template,
                     'gcpdiag.runbook.gce::permissions::instances_get')
    self.assertEqual(
        self.mock_add_child.call_args_list[1][0][0].__class__.__name__,
        'OsLoginStatusCheck')

  def test_iap_permissions_checked(self):
    self.op_get_values[flags.PROXY] = ssh.IAP
    step = ssh.GcpSshPermissions()
    step.execute()
    self.assertEqual(self.mock_add_child.call_args_list[-1][0][0].template,
                     'gcpdiag.runbook.gce::permissions::iap_role')


class OsLoginStatusCheckTest(SshStepTestBase):
  """Test OsLoginStatusCheck."""

  def setUp(self):
    super().setUp()
    self.mock_vm_metadata_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.generalized_steps.VmMetadataCheck',
                   autospec=True))
    self.mock_iam_policy_check = self.enterContext(
        mock.patch('gcpdiag.runbook.iam.generalized_steps.IamPolicyCheck',
                   autospec=True))
    self.mock_posix_user_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.PosixUserHasValidSshKeyCheck',
                   autospec=True))
    self.mock_duplicate_keys_check = self.enterContext(
        mock.patch('gcpdiag.runbook.gce.ssh.VmDuplicateSshKeysCheck',
                   autospec=True))
    self.mock_add_child = self.enterContext(
        mock.patch.object(ssh.OsLoginStatusCheck, 'add_child'))

  def test_ssh_key_in_metadata_path(self):
    self.op_get_values[ssh.ACCESS_METHOD] = ssh.SSH_KEY_IN_METADATA
    step = ssh.OsLoginStatusCheck()
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
    self.op_get_values[flags.POSIX_USER] = 'testuser'

  def test_valid_key_present(self):
    self.mock_instance.get_metadata.return_value = 'testuser:ssh-rsa AAA... testuser@host'
    self.mock_user_has_valid_ssh_key.return_value = True
    step = ssh.PosixUserHasValidSshKeyCheck()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_no_valid_key(self):
    self.mock_instance.get_metadata.return_value = 'otheruser:ssh-rsa BBB... otheruser@host'
    self.mock_user_has_valid_ssh_key.return_value = False
    step = ssh.PosixUserHasValidSshKeyCheck()
    step.execute()
    self.mock_op_add_failed.assert_called_once()


class VmDuplicateSshKeysCheckTest(SshStepTestBase):
  """Test VmDuplicateSshKeysCheck."""

  def test_no_ssh_keys(self):
    self.mock_instance.get_metadata.return_value = ''
    step = ssh.VmDuplicateSshKeysCheck()
    step.execute()
    self.mock_op_add_ok.assert_called_once()

  def test_duplicate_keys(self):
    ssh_keys = ('user1:ssh-rsa SAMEKEY... user1@host\n'
                'user2:ssh-rsa BBB... user2@host\n'
                'user3:ssh-rsa SAMEKEY... user3@host')
    self.mock_instance.get_metadata.return_value = ssh_keys
    step = ssh.VmDuplicateSshKeysCheck()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_no_duplicate_keys(self):
    ssh_keys = ('user1:ssh-rsa KEY1... user1@host\n'
                'ssh-rsa KEY2... user2@host\n\n'
                'user3:ssh-rsa KEY3... user3@host')
    self.mock_instance.get_metadata.return_value = ssh_keys
    step = ssh.VmDuplicateSshKeysCheck()
    step.execute()
    self.mock_op_add_ok.assert_called_once()


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
