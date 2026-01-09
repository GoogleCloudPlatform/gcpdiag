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
""" Test Kubectl Security """

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from gcpdiag import config
from gcpdiag.queries import gke, kubectl

class TestKubectlSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_cache_dir = config.get_cache_dir()
        config.set_cache_dir(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        config.set_cache_dir(self.original_cache_dir)

    def test_make_kube_config_permissions_new_file(self):
        # Mock Cluster object
        mock_cluster = MagicMock(spec=gke.Cluster)
        mock_cluster.name = 'test-cluster'
        mock_cluster.short_path = 'test-project/us-central1/test-cluster'
        mock_cluster.endpoint = '1.2.3.4'
        mock_cluster.cluster_ca_certificate = 'fake-ca-cert'

        executor = kubectl.KubectlExecutor(mock_cluster)

        # Execute make_kube_config
        executor.make_kube_config()

        config_path = kubectl.get_config_path()
        self.assertTrue(os.path.exists(config_path))

        # Check permissions
        st = os.stat(config_path)
        permissions = oct(st.st_mode & 0o777)
        self.assertEqual(permissions, '0o600')

    def test_make_kube_config_permissions_existing_file(self):
        # Create file with insecure permissions first
        config_path = kubectl.get_config_path()
        with open(config_path, 'w') as f:
            f.write("clusters: []\ncontexts: []")
        os.chmod(config_path, 0o644)

        st = os.stat(config_path)
        self.assertNotEqual(oct(st.st_mode & 0o777), '0o600')

        # Mock Cluster object
        mock_cluster = MagicMock(spec=gke.Cluster)
        mock_cluster.name = 'test-cluster'
        mock_cluster.short_path = 'test-project/us-central1/test-cluster'
        mock_cluster.endpoint = '1.2.3.4'
        mock_cluster.cluster_ca_certificate = 'fake-ca-cert'

        executor = kubectl.KubectlExecutor(mock_cluster)

        # Execute make_kube_config
        executor.make_kube_config()

        # Check permissions
        st = os.stat(config_path)
        permissions = oct(st.st_mode & 0o777)
        self.assertEqual(permissions, '0o600')
