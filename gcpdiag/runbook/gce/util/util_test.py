# Copyright 2023 Google LLC
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
""" Test Class for GCE runbook util"""
import unittest
from unittest import mock

import googleapiclient

from gcpdiag.queries import gce
from gcpdiag.runbook import exceptions as runbook_exceptions
from gcpdiag.runbook.gce import flags, util


class TestEnsureInstanceResolved(unittest.TestCase):
  """Test class for ensure_instance_resolved"""

  def setUp(self):
    super().setUp()
    self.mock_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_get_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_instance'))

  def test_instance_already_resolved(self):
    self.mock_get.side_effect = {
        flags.INSTANCE_ID: '123',
        flags.INSTANCE_NAME: 'test-instance'
    }.get
    util.ensure_instance_resolved()
    self.mock_get_instance.assert_not_called()

  def test_instance_resolved_by_name(self):
    instance = mock.MagicMock(spec=gce.Instance)
    instance.name = 'test-instance'
    instance.id = '123'
    self.mock_get_instance.return_value = instance
    self.mock_get.side_effect = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.INSTANCE_ID: None
    }.get
    util.ensure_instance_resolved()
    self.mock_get_instance.assert_called_with(project_id='test-project',
                                              zone='us-central1-a',
                                              instance_name='test-instance')
    self.mock_put.assert_any_call(flags.INSTANCE_NAME, 'test-instance')
    self.mock_put.assert_any_call(flags.INSTANCE_ID, '123')

  def test_instance_resolved_by_id(self):
    instance = mock.MagicMock(spec=gce.Instance)
    instance.name = 'test-instance'
    instance.id = '123'
    self.mock_get_instance.return_value = instance
    self.mock_get.side_effect = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: None,
        flags.INSTANCE_ID: '123'
    }.get
    util.ensure_instance_resolved()
    self.mock_get_instance.assert_called_with(project_id='test-project',
                                              zone='us-central1-a',
                                              instance_name='123')
    self.mock_put.assert_any_call(flags.INSTANCE_NAME, 'test-instance')
    self.mock_put.assert_any_call(flags.INSTANCE_ID, '123')

  def test_missing_parameters(self):
    self.mock_get.side_effect = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: None,
        flags.INSTANCE_ID: None
    }.get
    with self.assertRaises(runbook_exceptions.MissingParameterError):
      util.ensure_instance_resolved()

  def test_instance_not_found(self):
    self.mock_get.side_effect = {
        flags.PROJECT_ID: 'test-project',
        flags.ZONE: 'us-central1-a',
        flags.INSTANCE_NAME: 'test-instance',
        flags.INSTANCE_ID: None
    }.get
    mock_resp = mock.MagicMock(status=404)
    self.mock_get_instance.side_effect = googleapiclient.errors.HttpError(
        resp=mock_resp, content=b'')
    with self.assertRaises(runbook_exceptions.FailedStepError):
      util.ensure_instance_resolved()


class TestUtil():
  """Test Class for GCE runbook util """
  keys = [
      'test:ecdsa-sha2-nistp256 AA/NR0=',
      ('testuser:ssh-rsa AAA/HlFH+LC/+yt/yt/yt/yt+yt/yt+YT '
       'google-ssh {"userName":"testuser@company.com","expireOn":"2023-11-16T18:23:23+0000"}'
      )
  ]

  def test_has_at_least_one_valid_key(self):
    local_user = 'test'
    assert util.user_has_valid_ssh_key(local_user=local_user, keys=self.keys)

  def test_has_google_ssh_comment(self):
    # We don't check for gcloud/in browser ssh added keys
    local_user = 'testuser'
    assert util.user_has_valid_ssh_key(local_user=local_user, keys=self.keys)

  def test_has_no_valid_key(self):
    local_user = 'notvalid'
    assert not util.user_has_valid_ssh_key(local_user=local_user,
                                           keys=self.keys)

  def test_no_keys_present(self):
    local_user = 'notvalid'
    assert not util.user_has_valid_ssh_key(local_user=local_user, keys=[])

  def test_has_at_least_one_valid_key_and_type(self):
    local_user = 'test'
    key_type = 'ssh-rsa'
    assert util.user_has_valid_ssh_key(local_user=local_user,
                                       keys=self.keys,
                                       key_type=key_type)

  def test_has_at_least_one_valid_key_and_mismatched_type(self):
    local_user = 'test'
    key_type = 'ssh-dss'
    assert not util.user_has_valid_ssh_key(
        local_user=local_user, keys=self.keys, key_type=key_type)

  def test_regex_pattern_exist_in_logs(self):
    serial_log = ['one line of log', 'daemon [123]: started']
    pattern = [r'daemon \[\d+\]:']
    assert util.search_pattern_in_serial_logs(pattern, serial_log)
    pattern = [r'daemon \[\d+\]:', r'line (of|x)']
    assert util.search_pattern_in_serial_logs(pattern, serial_log, 'AND')

  def test_one_pattern_exist_in_logs(self):
    serial_log = ['one line of log', 'second string test']
    pattern = ['line', 'long']
    assert util.search_pattern_in_serial_logs(pattern, serial_log)
    pattern = ['line', r'log \w+']
    assert util.search_pattern_in_serial_logs(pattern, serial_log)
    pattern = ['line', r'log \w+']
    assert not util.search_pattern_in_serial_logs(pattern, [])

  def test_all_pattern_exist_logs(self):
    serial_log = ['one line of log', 'second 20 string', 'third']
    pattern = ['line', r'second \d+']
    assert util.search_pattern_in_serial_logs(pattern, serial_log, 'AND')
    pattern = [r'second \d+ \w+', 'third']
    assert util.search_pattern_in_serial_logs(pattern, serial_log, 'AND')
    pattern = [r'second \d+ \w+', 'third', 'invalid']
    assert not util.search_pattern_in_serial_logs(pattern, [], 'AND')
