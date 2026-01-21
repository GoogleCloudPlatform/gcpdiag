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

""" Tests for kubectl. """

import unittest
from unittest.mock import MagicMock, patch
import os
import shutil
import tempfile
import stat
from gcpdiag.queries import kubectl, gke

class TestKubectlExecutor(unittest.TestCase):
    def test_make_kube_config_permissions(self):
        # Mock cluster
        mock_cluster = MagicMock(spec=gke.Cluster)
        mock_cluster.name = 'test-cluster'
        mock_cluster.short_path = 'test-cluster-short'
        mock_cluster.endpoint = '1.2.3.4'
        mock_cluster.cluster_ca_certificate = 'fake-ca-cert'

        executor = kubectl.KubectlExecutor(mock_cluster)

        # Use a temporary directory for cache to avoid messing with real cache
        # Create a temp dir
        temp_dir = tempfile.mkdtemp()
        try:
             with patch('gcpdiag.config.get_cache_dir') as mock_get_cache_dir:
                 mock_get_cache_dir.return_value = temp_dir

                 # Run make_kube_config
                 executor.make_kube_config()

                 config_path = os.path.join(temp_dir, 'gcpdiag-config')
                 self.assertTrue(os.path.exists(config_path))

                 # Check permissions
                 st = os.stat(config_path)
                 # Check if permissions are 0600 (only owner can read/write)
                 # st_mode & 0o777 should be 0o600
                 permissions = st.st_mode & 0o777
                 print(f"Permissions: {oct(permissions)}")
                 self.assertEqual(permissions, 0o600)

        finally:
            shutil.rmtree(temp_dir)
