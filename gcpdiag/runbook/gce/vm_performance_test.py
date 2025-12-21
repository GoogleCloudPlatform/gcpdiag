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
"""Test class for gce/VmPerformance."""

import datetime
import json
import unittest
from unittest import mock

import googleapiclient.errors

from gcpdiag import config
from gcpdiag.queries import crm, gce
from gcpdiag.runbook import gce as gce_runbook
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.gce import flags, vm_performance


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = gce_runbook
  runbook_name = 'gce/vm-performance'
  config.init({'auto': True, 'interface': 'cli'})
  min_cpu_platform = 'Intel Ice Lake'

  rule_parameters = [
      {
          'project_id': 'gcpdiag-gce-vm-performance',
          'instance_name': 'faulty-linux-ssh',
          'zone': 'europe-west2-a',
      },
      {
          'project_id': 'gcpdiag-gce-vm-performance',
          'instance_name': 'faulty-windows-ssh',
          'zone': 'europe-west2-a',
      },
  ]


class VmPerformanceTest(unittest.TestCase):

  def test_legacy_parameter_handler(self):
    runbook = vm_performance.VmPerformance()
    parameters = {'name': 'test-instance', 'project_id': 'test-project'}
    runbook.legacy_parameter_handler(parameters)
    self.assertNotIn('name', parameters)
    self.assertIn('instance_name', parameters)
    self.assertEqual(parameters['instance_name'], 'test-instance')
    self.assertEqual(parameters['project_id'], 'test-project')


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    del kwargs
    return f'{key}'


class VmPerformanceStepTestBase(unittest.TestCase):
  """Base class for VM performance step tests."""

  def setUp(self):
    super().setUp()
    # enterContext will automatically clean up the patch
    self.mock_op_get = self.enterContext(mock.patch('gcpdiag.runbook.op.get'))
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_info = self.enterContext(mock.patch('gcpdiag.runbook.op.info'))
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
    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_monitoring_query = self.enterContext(
        mock.patch('gcpdiag.queries.monitoring.query'))
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_gce_get_all_disks_of_instance = self.enterContext(
        mock.patch('gcpdiag.queries.gce.get_all_disks_of_instance'))

    self.mock_instance = mock.Mock(spec=gce.Instance)
    self.mock_instance.project_id = 'test-project'
    self.mock_instance.zone = 'us-central1-a'
    self.mock_instance.name = 'test-instance'
    self.mock_instance.id = '12345'
    self.mock_instance.is_running = True
    self.mock_instance.disks = [{'deviceName': 'disk-1'}]
    self.mock_instance.machine_type.return_value = 'n1-standard-1'
    self.mock_instance.laststarttimestamp.return_value = (
        '2025-10-27T10:00:00.000000+00:00')
    self.mock_instance.laststoptimestamp.return_value = None
    self.mock_gce_get_instance.return_value = self.mock_instance
    self.mock_disk = mock.Mock(spec=gce.Disk)

    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.id = 'test-project'
    self.mock_crm_get_project.return_value = self.mock_project

    # Default side effect for op.get
    self.params = {
        flags.PROJECT_ID:
            'test-project',
        flags.ZONE:
            'us-central1-a',
        flags.INSTANCE_NAME:
            'test-instance',
        flags.START_TIME:
            datetime.datetime(2025, 10, 27, tzinfo=datetime.timezone.utc),
        flags.END_TIME:
            datetime.datetime(2025, 10, 28, tzinfo=datetime.timezone.utc),
    }
    self.mock_op_get.side_effect = lambda key, default=None: self.params.get(
        key, default)

    # Setup operator context
    mock_interface = mock.Mock()
    operator = op.Operator(mock_interface)
    operator.messages = MockMessage()
    operator.parameters = self.params
    self.enterContext(op.operator_context(operator))


class VmPerformanceStartTest(VmPerformanceStepTestBase):
  """Test VmPerformanceStart step."""

  def test_instance_running(self):
    step = vm_performance.VmPerformanceStart()
    step.execute()
    self.mock_gce_get_instance.assert_called_once_with(
        project_id='test-project',
        zone='us-central1-a',
        instance_name='test-instance',
    )
    self.mock_op_put.assert_called_with(flags.ID, '12345')
    self.mock_op_add_failed.assert_not_called()
    self.mock_op_add_skipped.assert_not_called()

  def test_instance_not_running(self):
    self.mock_instance.is_running = False
    self.mock_instance.status = 'TERMINATED'
    step = vm_performance.VmPerformanceStart()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  def test_instance_not_found(self):
    self.mock_gce_get_instance.side_effect = googleapiclient.errors.HttpError(
        mock.Mock(status=404), b'not found')
    step = vm_performance.VmPerformanceStart()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  def test_instance_name_missing_id_provided(self):
    self.params[flags.ID] = '12345'
    self.params[flags.INSTANCE_NAME] = None
    step = vm_performance.VmPerformanceStart()
    step.execute()
    self.mock_gce_get_instance.assert_called_once_with(
        project_id='test-project', zone='us-central1-a', instance_name=None)
    self.mock_op_put.assert_called_with(flags.INSTANCE_NAME, 'test-instance')


class DiskHealthCheckTest(VmPerformanceStepTestBase):
  """Test DiskHealthCheck step."""

  def test_healthy_disk(self):
    self.mock_monitoring_query.return_value = []
    step = vm_performance.DiskHealthCheck()
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_unhealthy_disk(self):
    self.mock_monitoring_query.return_value = [{'metric': 'data'}]
    step = vm_performance.DiskHealthCheck()
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_op_add_failed.assert_called_once()
    self.mock_op_add_ok.assert_not_called()


class CpuOvercommitmentCheckTest(VmPerformanceStepTestBase):
  """Test CpuOvercommitmentCheck step."""

  def setUp(self):
    super().setUp()
    self.mock_instance.is_sole_tenant_vm = False
    self.mock_instance.machine_type.return_value = 'e2-standard-2'
    self.mock_instance.min_cpu_platform.return_value = 'Intel Broadwell'

  def test_e2_cpu_not_overcommitted(self):
    self.mock_monitoring_query.side_effect = [
        # cpu_count_query result
        {
            'some_id': {
                'values': [[2]]
            }
        },
        # cpu_overcomit_metrics result
        [],
    ]
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.assertEqual(self.mock_monitoring_query.call_count, 2)
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_e2_cpu_overcommitted(self):
    self.mock_monitoring_query.side_effect = [
        # cpu_count_query result
        {
            'some_id': {
                'values': [[2]]
            }
        },
        # cpu_overcomit_metrics result
        [{
            'metric': 'data'
        }],
    ]
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.assertEqual(self.mock_monitoring_query.call_count, 2)
    self.mock_op_add_failed.assert_called_once()
    self.mock_op_add_ok.assert_not_called()

  def test_sole_tenant_cpu_not_overcommitted(self):
    self.mock_instance.is_sole_tenant_vm = True
    self.mock_instance.machine_type.return_value = 'n1-standard-1'
    self.mock_monitoring_query.side_effect = [
        {
            'some_id': {
                'values': [[1]]
            }
        },
        [],
    ]
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.assertEqual(self.mock_monitoring_query.call_count, 2)
    self.mock_op_add_ok.assert_called_once()

  def test_not_e2_or_sole_tenant_skipped(self):
    self.mock_instance.machine_type.return_value = 'n1-standard-1'
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.mock_monitoring_query.assert_not_called()
    self.mock_op_add_skipped.assert_called_once()

  def test_no_cpu_count_info(self):
    self.mock_monitoring_query.return_value = []
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_op_add_failed.assert_not_called()
    self.mock_op_add_ok.assert_not_called()
    self.mock_op_add_skipped.assert_not_called()
    self.mock_op_info.assert_called()

  @mock.patch('gcpdiag.runbook.gce.vm_performance.datetime')
  def test_instance_just_started_within_window(self, mock_datetime):
    # Mock current time to be close to laststarttimestamp
    mock_now = datetime.datetime(2025,
                                 10,
                                 27,
                                 10,
                                 2,
                                 0,
                                 tzinfo=datetime.timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.strptime.side_effect = datetime.datetime.strptime
    mock_datetime.timedelta = datetime.timedelta

    self.mock_instance.is_running = False
    self.mock_instance.laststoptimestamp.return_value = '2025-10-27T09:55:00.000000+00:00'
    self.mock_monitoring_query.side_effect = [
        {
            'some_id': {
                'values': [[2]]
            }
        },
        [],
    ]
    step = vm_performance.CpuOvercommitmentCheck()
    step.execute()
    self.assertEqual(self.mock_monitoring_query.call_count, 2)
    query_string = self.mock_monitoring_query.call_args_list[0][0][1]
    self.assertIn("within 9h, d'2025/10/27 09:55:00'", query_string)


class DiskAvgIOLatencyCheckTest(VmPerformanceStepTestBase):
  """Test DiskAvgIOLatencyCheck step."""

  def setUp(self):
    super().setUp()
    self.mock_disk = mock.Mock(spec=gce.Disk)
    self.mock_disk.name = 'disk-1'
    self.mock_disk.type = 'pd-balanced'
    self.mock_gce_get_all_disks_of_instance.return_value = {
        'disk-1': self.mock_disk
    }

  def test_latency_ok(self):
    self.mock_monitoring_query.return_value = []
    step = vm_performance.DiskAvgIOLatencyCheck()
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_op_add_ok.assert_called_once()
    self.mock_op_add_failed.assert_not_called()

  def test_latency_high(self):
    self.mock_monitoring_query.return_value = [{'metric': 'data'}]
    step = vm_performance.DiskAvgIOLatencyCheck()
    step.execute()
    self.mock_monitoring_query.assert_called_once()
    self.mock_op_add_failed.assert_called_once()
    self.mock_op_add_ok.assert_not_called()

  def test_unsupported_disk_type(self):
    self.mock_disk.type = 'local-ssd'
    step = vm_performance.DiskAvgIOLatencyCheck()
    step.execute()
    self.mock_monitoring_query.assert_not_called()
    self.mock_op_add_skipped.assert_called_once()


class CheckLiveMigrationsTest(VmPerformanceStepTestBase):
  """Test CheckLiveMigrations step."""

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.gce.vm_performance.CheckLiveMigrations.add_child'))

  def test_no_live_migrations(self):
    self.mock_logs_realtime_query.return_value = []
    step = vm_performance.CheckLiveMigrations()
    step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_op_add_ok.assert_called_once()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(
        self.add_child_patch.call_args[0][0],
        vm_performance.DiskIopsThroughputUtilisationChecks,
    )

  def test_live_migrations_found(self):
    self.mock_logs_realtime_query.return_value = [{
        'timestamp': '2025-10-27T11:00:00.000000Z'
    }]
    step = vm_performance.CheckLiveMigrations()
    step.execute()
    self.mock_logs_realtime_query.assert_called_once()
    self.mock_op_add_ok.assert_not_called()
    # add_child is called twice because one log means start_time,
    # log_time, end_time -> 3 entries -> 2 intervals
    self.assertEqual(self.add_child_patch.call_count, 2)
    self.assertIsInstance(
        self.add_child_patch.call_args_list[0][0][0],
        vm_performance.DiskIopsThroughputUtilisationChecks,
    )
    self.assertIsInstance(
        self.add_child_patch.call_args_list[1][0][0],
        vm_performance.DiskIopsThroughputUtilisationChecks,
    )


limits_per_gb_data = """{
 "iops": {
  "pd-balanced": {"Read IOPS per GiB": "6", "Write IOPS per GiB": "6"},
  "pd-ssd": {"Read IOPS per GiB": "30", "Write IOPS per GiB": "30"},
  "pd-standard": {"Read IOPS per GiB": "0.75", "Write IOPS per GiB": "1.5"},
  "pd-extreme": {"Read IOPS per GiB": "0", "Write IOPS per GiB": "0"}
 },
 "throughput": {
  "pd-balanced": {"Throughput per GiB (MiBps)": "0.28"},
  "pd-ssd": {"Throughput per GiB (MiBps)": "0.48"},
  "pd-standard": {"Throughput per GiB (MiBps)": "0.12"},
  "pd-extreme": {"Throughput per GiB (MiBps)": "0"}
 },
 "baseline": {
  "pd-balanced": {"Baseline IOPS per VM": "0", "Baseline Throughput (MiBps) per VM": "0"},
  "pd-ssd": {"Baseline IOPS per VM": "0", "Baseline Throughput (MiBps) per VM": "0"},
  "pd-standard": {"Baseline IOPS per VM": "0", "Baseline Throughput (MiBps) per VM": "0"},
  "pd-extreme": {"Baseline IOPS per VM": "0", "Baseline Throughput (MiBps) per VM": "0"}
 }
}"""
n_family_data = """{
"N1 VMs": {"pd-balanced": [{"VM vCPU count": "1", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}],
"pd-standard": [{"VM vCPU count": "1", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]},
"N2 VMs": {"pd-extreme": [{"Machine type": "n2-standard-80", "Maximum read IOPS": 100000,
"Maximum write IOPS": 100000, "Maximum read throughput (MiBps)": 4000,
"Maximum write throughput (MiBps)": 4000}],
"pd-standard": [{"VM vCPU count": "1", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]},
"N2D VMs": {"pd-standard": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]}
}"""
c_family_data = """{
"C2 VMs": {"pd-ssd": [{"VM vCPU count": "4", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]},
"C3 VMs": {"pd-ssd": [{"VM vCPU count": "4", "Maximum read IOPS": 25000,
"Maximum write IOPS": 25000, "Maximum read throughput (MiBps)": 1200,
"Maximum write throughput (MiBps)": 1200}]}
}"""
t_family_data = """{
"T2D VMs": {"pd-standard": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]},
"T2A VMs": {"pd-standard": [{"VM vCPU count": "4-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]}
}"""

e_family_data = """{
"E2 VMs": {"pd-balanced": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}],
"pd-ssd": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}],
"pd-extreme": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}],
"pd-standard": [{"VM vCPU count": "2-7", "Maximum read IOPS": 15000,
"Maximum write IOPS": 15000, "Maximum read throughput (MiBps)": 240,
"Maximum write throughput (MiBps)": 240}]}
}"""
a_family_data = """{
"A2 VMs": {"pd-balanced": [{"Machine type": "a2-highgpu-1g", "Maximum read IOPS": 3000,
"Maximum write IOPS": 3000, "Maximum read throughput (MiBps)": 120,
"Maximum write throughput (MiBps)": 120}]},
"A2 Ultra VMs": {"pd-balanced": [{"Machine type": "a2-ultragpu-1g", "Maximum read IOPS": 3000,
"Maximum write IOPS": 3000, "Maximum read throughput (MiBps)": 120,
"Maximum write throughput (MiBps)": 120}]},
"F1 VMs": {},
"G2 VMs": {},
"M1 VMs": {"pd-ssd": [{"Machine type": "m1-ultramem-40", "Maximum read IOPS": 60000,
"Maximum write IOPS": 60000, "Maximum read throughput (MiBps)": 1200,
"Maximum write throughput (MiBps)": 1200}]},
"M2 VMs": {},
"M3 VMs": {}
}"""


class DiskIopsThroughputUtilisationChecksTest(VmPerformanceStepTestBase):
  """Test DiskIopsThroughputUtilisationChecks step."""

  def setUp(self):
    super().setUp()
    self.mock_disk = mock.Mock(spec=gce.Disk)
    self.mock_disk.name = 'disk-1'
    self.mock_disk.type = 'pd-balanced'
    self.mock_disk.size = 100
    self.mock_disk.provisionediops = 0
    self.mock_gce_get_all_disks_of_instance.return_value = {
        'disk-1': self.mock_disk
    }
    self.mock_monitoring_query.side_effect = [
        # cpu_count_query
        {
            '1': {
                'values': [[1]]
            }
        },
        # actual_usage_comparison query 1
        [],
        # actual_usage_comparison query 2
        [],
        # actual_usage_comparison query 3
        [],
        # actual_usage_comparison query 4
        [],
    ]

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_n1_pd_balanced_ok(self, mock_json_load):
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    # 1 call for cpu count, 4 for usage comparison
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_c2_pd_ssd_ok(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'c2-standard-4'
    self.mock_monitoring_query.side_effect = [{
        '1': {
            'values': [[4]]
        }
    }, [], [], [], []]
    self.mock_disk.type = 'pd-ssd'
    self.mock_gce_get_all_disks_of_instance.return_value = {
        'disk-1': self.mock_disk
    }
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(c_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    # 1 call for cpu count, 4 for usage comparison
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_n1_pd_balanced_high_usage(self, mock_json_load):
    self.mock_monitoring_query.side_effect = [
        # cpu_count_query
        {
            '1': {
                'values': [[1]]
            }
        },
        # actual_usage_comparison query 1 (read iops) -> high usage
        {
            'some_id': {
                'values': [['val1'], ['val2'], ['val3']]
            }
        },
        # actual_usage_comparison query 2 (read throughput) -> ok
        {},
        # actual_usage_comparison query 3 (write iops) -> high usage
        {
            'some_id': {
                'values': [['val1'], ['val2'], ['val3']]
            }
        },
        # actual_usage_comparison query 4 (write throughput) -> ok
        {},
    ]
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_failed.call_count, 2)
    self.assertEqual(self.mock_op_add_ok.call_count, 2)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_t2d_pd_standard_ok(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 't2d-standard-4'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[4]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-standard'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(t_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_e2_pd_balanced_ok(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'e2-standard-4'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[4]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-balanced'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(e_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_n2_pd_extreme_ok(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'n2-standard-80'  # > 63 cpus
    self.mock_disk.type = 'pd-extreme'
    self.mock_disk.provisionediops = 50000
    self.mock_monitoring_query.side_effect = [
        # cpu_count_query
        {
            '1': {
                'values': [[80]]
            }
        },
        # actual_usage_comparison queries
        {},
        {},
        {},
        {},
    ]
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_unsupported_machine_type(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'x1-standard-1'
    # we need to mock the cpu count query
    self.mock_monitoring_query.side_effect = [{'1': {'values': [[1]]}}]
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.mock_op_add_failed.assert_called_once()
    self.assertEqual(mock_json_load.call_count, 2)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_custom_machine_type(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'custom-2-4096'
    self.mock_monitoring_query.side_effect = [{
        '1': {
            'values': [[2]]
        }
    }, [], [], [], []]
    self.mock_disk.type = 'pd-balanced'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_g1_small_unsupported_family(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'g1-small'
    self.mock_disk.type = 'pd-extreme'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(a_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.mock_op_add_failed.assert_called_once()

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_e2_medium_machine_type(self, mock_json_load):
    self.mock_instance.machine_type.return_value = 'e2-medium'
    self.mock_monitoring_query.side_effect = [{
        '1': {
            'values': [[2]]
        }
    }, [], [], [], []]
    self.mock_disk.type = 'pd-balanced'
    # Adjust mock to return a valid structure for e2-medium
    e_family_data_medium = json.loads(e_family_data)
    e_family_data_medium['E2 VMs']['pd-balanced'] = [{
        'VM vCPU count': 'e2-medium*',
        'Maximum read IOPS': 15000,
        'Maximum write IOPS': 15000,
        'Maximum read throughput (MiBps)': 240,
        'Maximum write throughput (MiBps)': 240
    }]
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        e_family_data_medium,
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('gcpdiag.runbook.gce.vm_performance.datetime')
  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_instance_just_stopped_window(self, mock_json_load, mock_datetime):
    # Mock current time to be close to laststarttimestamp
    mock_now = datetime.datetime(2025,
                                 10,
                                 27,
                                 10,
                                 2,
                                 0,
                                 tzinfo=datetime.timezone.utc)
    mock_datetime.now.return_value = mock_now
    mock_datetime.strptime.side_effect = datetime.datetime.strptime
    mock_datetime.timedelta = datetime.timedelta

    self.mock_instance.is_running = False
    self.mock_instance.laststoptimestamp.return_value = (
        '2025-10-27T09:55:00.000000+00:00')
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    query_string = self.mock_monitoring_query.call_args_list[0][0][1]
    self.assertIn("within 9h, d'2025/10/27 09:55:00'", query_string)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_actual_usage_comparision_http_error(self, mock_json_load):
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[1]]
            }
        },  # CPU count
        googleapiclient.errors.HttpError(
            mock.Mock(status=500),
            b'internal error'),  # actual_usage_comparision
        googleapiclient.errors.HttpError(mock.Mock(status=500),
                                         b'internal error'),
        googleapiclient.errors.HttpError(mock.Mock(status=500),
                                         b'internal error'),
        googleapiclient.errors.HttpError(mock.Mock(status=500),
                                         b'internal error'),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(self.mock_op_add_skipped.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_t2a_machine_types(self, mock_json_load):
    """Targets logic for T2A machine types."""
    self.mock_instance.machine_type.return_value = 't2a-standard-4'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[4]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-standard'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(t_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_m_family_machine_types(self, mock_json_load):
    """Targets logic for M family machine types."""
    self.mock_instance.machine_type.return_value = 'm1-ultramem-40'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[40]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-ssd'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(a_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_c3_machine_types_pd_extreme(self, mock_json_load):
    """Targets logic for C3 machine types with pd-extreme."""
    self.mock_instance.machine_type.return_value = 'c3-standard-4'
    self.mock_monitoring_query.side_effect = [{
        '1': {
            'values': [[4]]
        }
    }, [], [], [], []]
    self.mock_disk.type = 'pd-extreme'
    self.mock_disk.provisionediops = 10000
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(c_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_n2d_machine_types_pd_standard(self, mock_json_load):
    """Targets logic for N2D machine types with pd-standard."""
    self.mock_instance.machine_type.return_value = 'n2d-standard-2'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[2]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-standard'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_e2_pd_extreme(self, mock_json_load):
    """Targets logic for E2 machine types with pd-extreme."""
    self.mock_instance.machine_type.return_value = 'e2-standard-4'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[4]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-extreme'
    self.mock_disk.provisionediops = 12000
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(e_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_limit_calculator_iops_write(self, mock_json_load):
    """Targets limit_calculator to ensure write IOPS are returned correctly."""
    self.mock_instance.machine_type.return_value = 'n1-standard-1'
    self.mock_disk.type = 'pd-balanced'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    # Directly test limit_calculator
    limits_data_loaded = json.loads(limits_per_gb_data)
    mach_fam_json_data_loaded = json.loads(n_family_data)
    results = step.limit_calculator(
        limits_data_loaded,
        mach_fam_json_data_loaded,
        'pd-balanced',
        100,
        'N1 VMs',
        'VM vCPU count',
        '1',
    )
    self.assertEqual(results[5], 15000)  # max_write_iops
    self.assertEqual(results[4], 600)  # vm_baseline_performance_w_iops


class VmPerformanceEndTest(VmPerformanceStepTestBase):
  """Test VmPerformanceEnd step."""

  def setUp(self):
    super().setUp()
    self.mock_op_prompt = self.enterContext(
        mock.patch('gcpdiag.runbook.op.prompt'))
    self.mock_config_get = self.enterContext(mock.patch('gcpdiag.config.get'))

  def test_end_step_no_interactive_mode_no_answer(self):
    self.mock_config_get.return_value = False
    self.mock_op_prompt.return_value = op.NO
    step = vm_performance.VmPerformanceEnd()
    step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_op_info.assert_called_once()

  def test_end_step_no_interactive_mode_yes_answer(self):
    self.mock_config_get.return_value = False
    self.mock_op_prompt.return_value = op.YES
    step = vm_performance.VmPerformanceEnd()
    step.execute()
    self.mock_op_prompt.assert_called_once()
    self.mock_op_info.assert_not_called()

  def test_end_step_interactive_mode(self):
    self.mock_config_get.return_value = True
    step = vm_performance.VmPerformanceEnd()
    step.execute()
    self.mock_op_prompt.assert_not_called()


class VmPerformanceBuildTreeTest(unittest.TestCase):

  @mock.patch('gcpdiag.runbook.gce.vm_performance.VmPerformance.add_step')
  @mock.patch('gcpdiag.runbook.gce.vm_performance.VmPerformance.add_start')
  @mock.patch('gcpdiag.runbook.gce.vm_performance.VmPerformance.add_end')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_build_tree(self, mock_op_get, mock_add_end, mock_add_start,
                      mock_add_step):
    mock_op_get.return_value = 'test_value'
    runbook = vm_performance.VmPerformance()
    runbook.build_tree()

    mock_add_start.assert_called_once()
    self.assertIsInstance(mock_add_start.call_args[1]['step'],
                          vm_performance.VmPerformanceStart)

    # Verify that all expected steps are added
    step_instances = [call[1]['child'] for call in mock_add_step.call_args_list]
    self.assertTrue(
        any(
            isinstance(s, gce_runbook.generalized_steps.HighVmCpuUtilization)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, gce_runbook.generalized_steps.HighVmMemoryUtilization)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, gce_runbook.generalized_steps.HighVmDiskUtilization)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, vm_performance.CpuOvercommitmentCheck)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, vm_performance.DiskHealthCheck)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, vm_performance.DiskAvgIOLatencyCheck)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, gce_runbook.generalized_steps.VmSerialLogsCheck)
            for s in step_instances))
    self.assertTrue(
        any(
            isinstance(s, vm_performance.CheckLiveMigrations)
            for s in step_instances))

    mock_add_end.assert_called_once()
    self.assertIsInstance(mock_add_end.call_args[1]['step'],
                          vm_performance.VmPerformanceEnd)


class VmPerformanceCoverageTest(VmPerformanceStepTestBase):
  """Additional coverage tests for the complex disk logic."""

  def setUp(self):
    super().setUp()
    # Mock CPU count to be generic
    self.mock_monitoring_query.return_value = {
        '1': {
            'values': [[4]]
        }  # 4 vCPUs default
    }
    self.mock_disk = mock.Mock(spec=gce.Disk)
    self.mock_disk.name = 'disk-1'
    self.mock_disk.size = 200
    self.mock_disk.provisionediops = 0
    self.mock_gce_get_all_disks_of_instance.return_value = {
        'disk-1': self.mock_disk
    }

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_pd_standard_small_disk_limits(self, mock_json_load):
    """Targets logic for pd-standard disks < 100GB."""
    self.mock_disk.type = 'pd-standard'
    self.mock_disk.size = 50  # < 100GB trigger
    self.mock_instance.machine_type.return_value = 'n1-standard-4'

    # Mock JSON return
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data)
    ]

    # Mock monitoring query chain
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[4]]
            }
        },
        {
            'some_id': {
                'values': [['9999'], ['9999'], ['9999']]
            }
        },
        {},
        {},
        {},
    ]

    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()

    self.mock_op_add_failed.assert_called_once()
    self.assertEqual(self.mock_op_add_ok.call_count, 3)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_pd_extreme_n2_high_cpu(self, mock_json_load):
    """Targets pd-extreme logic for N2 VMs > 63 CPUs."""
    self.mock_disk.type = 'pd-extreme'
    self.mock_disk.provisionediops = 50000
    self.mock_instance.machine_type.return_value = 'n2-standard-80'

    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]

    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[80]]
            }
        },
        {},
        {},
        {},
        {},
    ]

    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_unsupported_disk_type(self, mock_json_load):
    """Targets the skipped block for unsupported disk types."""
    self.mock_disk.type = 'pd-unknown'
    self.mock_monitoring_query.return_value = {'1': {'values': [[1]]}}

    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(n_family_data),
    ]

    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.mock_op_add_skipped.assert_called_once()

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_a2_pd_balanced_ok(self, mock_json_load):
    """Targets logic for A2 machine types."""
    self.mock_instance.machine_type.return_value = 'a2-highgpu-1g'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[8]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-balanced'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(a_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)

  @mock.patch('builtins.open', mock.mock_open())
  @mock.patch('json.load')
  def test_a2_ultragpu_machine_type(self, mock_json_load):
    """Targets logic for A2 UltraGPU machine types."""
    self.mock_instance.machine_type.return_value = 'a2-ultragpu-1g'
    self.mock_monitoring_query.side_effect = [
        {
            '1': {
                'values': [[12]]
            }
        },
        [],
        [],
        [],
        [],
    ]
    self.mock_disk.type = 'pd-balanced'
    mock_json_load.side_effect = [
        json.loads(limits_per_gb_data),
        json.loads(a_family_data),
    ]
    step = vm_performance.DiskIopsThroughputUtilisationChecks()
    step.execute()
    self.assertEqual(mock_json_load.call_count, 2)
    self.assertEqual(self.mock_monitoring_query.call_count, 5)
    self.assertEqual(self.mock_op_add_ok.call_count, 4)


if __name__ == '__main__':
  unittest.main()
