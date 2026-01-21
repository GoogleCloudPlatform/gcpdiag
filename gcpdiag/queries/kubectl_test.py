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

"""Tests for gcpdiag.queries.kubectl."""

import os
import shutil
import stat
import tempfile
from unittest import mock

from gcpdiag.queries import gke, kubectl

@mock.patch('gcpdiag.queries.kubectl.config.get_cache_dir')
class TestKubectlPermissions:
  """Test cases for kubectl configuration file permissions."""

  def setup_method(self):
    self.test_dir = tempfile.mkdtemp()
    self.mock_cluster = mock.MagicMock(spec=gke.Cluster)
    self.mock_cluster.name = "test-cluster"
    self.mock_cluster.short_path = "test-cluster"
    self.mock_cluster.endpoint = "1.2.3.4"
    self.mock_cluster.cluster_ca_certificate = "fake-ca-cert"

  def teardown_method(self):
    shutil.rmtree(self.test_dir)

  def test_make_kube_config_permissions(self, mock_get_cache_dir):
    mock_get_cache_dir.return_value = self.test_dir
    executor = kubectl.KubectlExecutor(self.mock_cluster)

    # Execute make_kube_config
    executor.make_kube_config()

    # Check file permissions
    config_path = os.path.join(self.test_dir, 'gcpdiag-config')
    assert os.path.exists(config_path)

    file_stat = os.stat(config_path)
    permissions = file_stat.st_mode & 0o777

    # Check if permissions are strictly 0600 (owner read/write only)
    assert permissions == 0o600

  def test_make_kube_config_overwrite_permissions(self, mock_get_cache_dir):
    """Ensure existing file with bad permissions is corrected."""
    mock_get_cache_dir.return_value = self.test_dir
    config_path = os.path.join(self.test_dir, 'gcpdiag-config')

    # Create file with bad permissions (0666)
    with open(config_path, 'w') as f:
        # We need a valid structure because make_kube_config reads it
        f.write("clusters: []\ncontexts: []\n")
    os.chmod(config_path, 0o666)

    executor = kubectl.KubectlExecutor(self.mock_cluster)
    executor.make_kube_config()

    file_stat = os.stat(config_path)
    permissions = file_stat.st_mode & 0o777

    assert permissions == 0o600
