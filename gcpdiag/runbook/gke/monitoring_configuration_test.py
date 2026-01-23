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
"""Test class for gke/GkeMonitoring."""

import unittest
from unittest import mock

from gcpdiag import config
from gcpdiag.runbook import gke, op, snapshot_test_base
from gcpdiag.runbook.gke import flags, monitoring_configuration


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gke
  runbook_name = 'gke/monitoring-configuration'
  project_id = 'mytestproject-371511'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [{
      'project_id': 'mytestproject-371511',
      'gke_cluster_name': 'cluster-2',
      'location': 'us-central1-a',
  }]


class MockCluster:
  """Mock GKE cluster for testing."""

  def __init__(
      self,
      name,
      location,
      is_autopilot=False,
      monitoring_enabled=True,
      metrics=None,
  ):
    self.name = name
    self.location = location
    self.is_autopilot = is_autopilot
    self._monitoring_enabled = monitoring_enabled
    self._metrics = metrics or []
    self.nodepools = []
    self.full_path = f'projects/p/locations/{location}/clusters/{name}'

  def has_monitoring_enabled(self):
    return self._monitoring_enabled

  def enabled_monitoring_components(self):
    return self._metrics

  def __str__(self):
    return self.full_path


class MockNodePool:
  """Mock GKE node pool for testing."""

  def __init__(self, taints=None):
    self._resource_data = {'config': {'taints': taints or []}}


class TestMonitoringConfiguration(unittest.TestCase):
  """Test class for monitoring_configuration runbook."""

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_no_clusters(self, mock_skipped, mock_crm, mock_gke,
                                  mock_get):
    """Test behavior when no clusters are found in the project."""
    del mock_crm, mock_get  # unused
    mock_gke.return_value = {}
    step = monitoring_configuration.MonitoringConfigurationStart()

    with op.operator_context(mock.Mock(parameters={'project_id': 'proj-1'})):
      step.execute()

    mock_skipped.assert_called_once()
    self.assertIn('No GKE clusters found', mock_skipped.call_args[1]['reason'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  def test_start_step_cluster_not_found_with_name_and_location(
      self, mock_skipped, mock_crm, mock_gke, mock_get):
    """Test behavior when a specific cluster name/location is provided but doesn't exist."""
    del mock_crm  # unused
    mock_get.side_effect = {
        flags.PROJECT_ID: 'p1',
        flags.GKE_CLUSTER_NAME: 'missing-cluster',
        flags.LOCATION: 'us-central1',
    }.get
    mock_gke.return_value = {'c1': MockCluster('other', 'us-east1')}
    step = monitoring_configuration.MonitoringConfigurationStart()

    with op.operator_context(
        mock.Mock(
            parameters={
                'project_id': 'p1',
                'gke_cluster_name': 'missing-cluster',
                'location': 'us-central1'
            })):
      step.execute()

    mock_skipped.assert_called_once()
    self.assertIn('does not exist', mock_skipped.call_args[1]['reason'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  def test_cluster_monitoring_entirely_disabled(self, mock_failed, mock_util,
                                                mock_gke, mock_get):
    """Test failure when monitoring is completely disabled at the cluster level."""
    del mock_gke, mock_get  # unused
    cluster = MockCluster('c1', 'loc1', monitoring_enabled=False)
    mock_util.return_value = cluster
    step = monitoring_configuration.ClusterLevelMonitoringConfigurationEnabled()

    with op.operator_context(mock.Mock(parameters={'project_id': 'p'})):
      step.execute()

    mock_failed.assert_called_once()
    self.assertIn('Monitoring entirely disabled',
                  mock_failed.call_args[1]['remediation'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.runbook.op.add_failed')
  def test_cluster_monitoring_missing_gpu_metrics(self, mock_failed, mock_util,
                                                  mock_gke, mock_get):
    """Test failure when DCGM metrics are missing for a cluster with GPU taints."""
    del mock_gke, mock_get  # unused
    cluster = MockCluster('gpu-c', 'loc1', metrics=['SYSTEM_COMPONENTS'])
    gpu_taint = {
        'key': 'nvidia.com/gpu',
        'value': 'present',
        'effect': 'NO_SCHEDULE'
    }
    cluster.nodepools = [MockNodePool(taints=[gpu_taint])]
    mock_util.return_value = cluster
    step = monitoring_configuration.ClusterLevelMonitoringConfigurationEnabled()

    with op.operator_context(mock.Mock(parameters={'project_id': 'p'})):
      step.execute()

    mock_failed.assert_called_once()
    self.assertIn('DCGM', mock_failed.call_args[1]['remediation'])

  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_cluster_monitoring_autopilot_skipped(self, mock_ok, mock_util,
                                                mock_gke, mock_get):
    """Test that Autopilot clusters are correctly identified as fully enabled (logic skip)."""
    del mock_gke, mock_get  # unused
    cluster = MockCluster('auto-c', 'loc1', is_autopilot=True)
    mock_util.return_value = cluster
    step = monitoring_configuration.ClusterLevelMonitoringConfigurationEnabled()

    with op.operator_context(mock.Mock(parameters={'project_id': 'p'})):
      step.execute()

    mock_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prompt')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_end_step_user_not_satisfied(self, mock_info, mock_prompt):
    """Test behavior when the user indicates they are not satisfied with the RCA."""

    mock_prompt.return_value = op.NO
    step = monitoring_configuration.MonitoringConfigurationEnd()

    step.execute()

    mock_info.assert_called_with(message=op.END_MESSAGE)


class TestMonitoringConfigurationCoverage(unittest.TestCase):
  """Unit tests to achieve 100% coverage for monitoring_configuration.py."""

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.add_skipped')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_start_execute_no_clusters(self, mock_op_get, mock_add_skipped,
                                     mock_get_clusters, mock_get_project):
    """Covers lines 75-81: Behavior when no clusters are found in the project."""
    mock_op_get.side_effect = {flags.PROJECT_ID: 'test-project'}.get
    mock_get_clusters.return_value = {}
    mock_get_project.return_value = 'projects/test-project'
    step = monitoring_configuration.MonitoringConfigurationStart()

    with op.operator_context(
        mock.Mock(parameters={'project_id': 'test-project'})):
      step.execute()

    mock_add_skipped.assert_called_once()
    self.assertIn('No GKE clusters found',
                  mock_add_skipped.call_args[1]['reason'])

  @mock.patch('gcpdiag.queries.crm.get_project')
  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_start_execute_with_parameters(self, mock_op_get, mock_get_clusters,
                                         mock_get_project):
    """Covers lines 87-93: Parameter retrieval and flag initialization."""
    # Arrange
    del mock_get_project  # unused
    mock_op_get.side_effect = {
        flags.PROJECT_ID: 'test-project',
        flags.GKE_CLUSTER_NAME: 'cluster-1',
        flags.LOCATION: 'us-central1',
    }.get
    mock_get_clusters.return_value = {
        'c1': MockCluster('cluster-1', 'us-central1')
    }
    step = monitoring_configuration.MonitoringConfigurationStart()

    with op.operator_context(
        mock.Mock(
            parameters={
                'project_id': 'test-project',
                'gke_cluster_name': 'cluster-1',
                'location': 'us-central1'
            })):
      step.execute()

  @mock.patch('gcpdiag.queries.gke.get_clusters')
  @mock.patch('gcpdiag.runbook.op.get')
  @mock.patch('gcpdiag.lint.gke.util.get_cluster_object')
  @mock.patch('gcpdiag.runbook.op.add_ok')
  def test_cluster_level_monitoring_standard_path(self, mock_add_ok,
                                                  mock_get_cluster_obj,
                                                  mock_op_get,
                                                  mock_get_clusters):
    """Covers lines 140-160: Step execution for a standard GKE cluster."""
    del mock_get_clusters  # unused
    mock_op_get.side_effect = {
        flags.LOCATION: 'us-central1',
        flags.GKE_CLUSTER_NAME: 'cluster-1'
    }.get

    metrics = [
        'CADVISOR',
        'DAEMONSET',
        'DEPLOYMENT',
        'HPA',
        'KUBELET',
        'POD',
        'STATEFULSET',
        'STORAGE',
        'SYSTEM_COMPONENTS',
    ]
    cluster = MockCluster('cluster-1',
                          'us-central1',
                          is_autopilot=False,
                          metrics=metrics)
    mock_get_cluster_obj.return_value = cluster
    step = monitoring_configuration.ClusterLevelMonitoringConfigurationEnabled()

    with op.operator_context(
        mock.Mock(
            parameters={
                'project_id': 'p',
                'location': 'us-central1',
                'gke_cluster_name': 'cluster-1'
            })):
      step.execute()

    mock_add_ok.assert_called_once()

  @mock.patch('gcpdiag.runbook.op.prompt')
  @mock.patch('gcpdiag.runbook.op.info')
  def test_end_execute_satisfied(self, mock_op_info, mock_op_prompt):
    """Covers line 242: Execution of the end step."""
    del mock_op_info  # unused

    mock_op_prompt.return_value = op.YES
    step = monitoring_configuration.MonitoringConfigurationEnd()

    step.execute()

    mock_op_prompt.assert_called_once()
