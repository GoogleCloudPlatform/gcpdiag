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
"""Test class for dataproc/SparkJob."""

import datetime
import unittest
from unittest import mock

from gcpdiag import config, utils
from gcpdiag.queries import apis_stub, crm, dataproc
from gcpdiag.runbook import dataproc as dataproc_rb
from gcpdiag.runbook import op, snapshot_test_base
from gcpdiag.runbook.dataproc import flags
from gcpdiag.runbook.dataproc import generalized_steps as dp_gs
from gcpdiag.runbook.dataproc import spark_job_failures
from gcpdiag.runbook.iam import generalized_steps as iam_gs

DUMMY_PROJECT_ID = 'gcpdiag-dataproc1-aaaa'


class Test(snapshot_test_base.RulesSnapshotTestBase):
  rule_pkg = dataproc_rb
  runbook_name = 'dataproc/spark-job-failures'
  project_id = 'gcpdiag-dataproc1-aaaa'
  success_job_id = '1234567890'
  failed_job_id = '1234567891'
  config.init({'auto': True, 'interface': 'cli'}, project_id)

  rule_parameters = [
      {
          'project_id': DUMMY_PROJECT_ID,
          'dataproc_cluster_name': 'job_failed',
          'region': 'us-central1',
          'job_id': failed_job_id,
      },
      {
          'project_id': DUMMY_PROJECT_ID,
          'dataproc_cluster_name': 'job-not-failed',
          'region': 'us-central1',
          'job_id': success_job_id,
      },
  ]


class MockMessage:
  """Mock messages for testing."""

  def get_msg(self, key, **kwargs):
    return f'{key}: {kwargs}'


class SparkJobFailuresTest(unittest.TestCase):

  def test_legacy_parameter_handler(self):
    runbook = spark_job_failures.SparkJobFailures()
    parameters = {'job_id': 'test-job', 'project_id': 'test-project'}
    runbook.legacy_parameter_handler(parameters)
    self.assertNotIn('job_id', parameters)
    self.assertIn('dataproc_job_id', parameters)
    self.assertEqual(parameters['dataproc_job_id'], 'test-job')


class SparkJobFailuresBuildTreeTest(unittest.TestCase):

  @mock.patch(
      'gcpdiag.runbook.dataproc.spark_job_failures.SparkJobFailures.add_step')
  @mock.patch(
      'gcpdiag.runbook.dataproc.spark_job_failures.SparkJobFailures.add_start')
  @mock.patch(
      'gcpdiag.runbook.dataproc.spark_job_failures.SparkJobFailures.add_end')
  @mock.patch('gcpdiag.runbook.op.get')
  def test_build_tree(self, mock_op_get, mock_add_end, mock_add_start,
                      mock_add_step):
    mock_op_get.return_value = 'test_value'
    runbook = spark_job_failures.SparkJobFailures()
    runbook.build_tree()
    mock_add_start.assert_called_once()
    self.assertIsInstance(mock_add_start.call_args[0][0],
                          spark_job_failures.JobStart)
    mock_add_step.assert_called_once()
    self.assertIsInstance(
        mock_add_step.call_args[1]['child'],
        spark_job_failures.JobDetailsDependencyGateway,
    )
    mock_add_end.assert_called_once()
    self.assertIsInstance(mock_add_end.call_args[0][0],
                          spark_job_failures.SparkJobEnd)


class SparkJobFailuresStepTestBase(unittest.TestCase):
  """Base class for Spark Job Failures step tests."""

  def setUp(self):
    super().setUp()
    # 1. Patch get_api with the stub.
    self.enterContext(
        mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub))
    # 2. Create a mock interface to capture outputs
    self.mock_interface = mock.create_autospec(op.InteractionInterface,
                                               instance=True)
    self.mock_interface.rm = mock.Mock()
    # 3. Instantiate a real Operator
    self.operator = op.Operator(self.mock_interface)
    self.operator.run_id = 'test-run'
    self.operator.messages = MockMessage()
    # 4. Define standard parameters.
    self.params = {
        flags.PROJECT_ID:
            DUMMY_PROJECT_ID,
        flags.REGION:
            'us-central1',
        flags.DATAPROC_JOB_ID:
            '1234567891',
        'cluster_exists':
            False,
        flags.JOB_OLDER_THAN_30_DAYS:
            False,
        flags.SERVICE_ACCOUNT:
            None,
        flags.CROSS_PROJECT_ID:
            None,
        flags.STACKDRIVER:
            False,
        'start_time':
            datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
        'end_time':
            datetime.datetime(2025, 1, 2, tzinfo=datetime.timezone.utc),
    }
    self.operator.parameters = self.params
    self.mock_op_put = self.enterContext(mock.patch('gcpdiag.runbook.op.put'))
    self.mock_op_put.side_effect = self.params.__setitem__

    self.mock_crm_get_project = self.enterContext(
        mock.patch('gcpdiag.queries.crm.get_project'))
    self.mock_dataproc_get_job_by_jobid = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_job_by_jobid'))
    self.mock_dataproc_get_cluster = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_cluster'))
    self.mock_iam_is_service_account_existing = self.enterContext(
        mock.patch('gcpdiag.queries.iam.is_service_account_existing'))
    self.mock_logs_realtime_query = self.enterContext(
        mock.patch('gcpdiag.queries.logs.realtime_query'))
    self.mock_dp_extract_supported_version = self.enterContext(
        mock.patch(
            'gcpdiag.queries.dataproc.extract_dataproc_supported_version'))
    self.mock_dp_get_autoscaling_policy = self.enterContext(
        mock.patch('gcpdiag.queries.dataproc.get_auto_scaling_policy'))
    self.mock_dp_extract_bq_version = self.enterContext(
        mock.patch(
            'gcpdiag.queries.dataproc.extract_dataproc_bigquery_version'))

    self.mock_project = mock.Mock(spec=crm.Project)
    self.mock_project.id = 'test-project'
    self.mock_crm_get_project.return_value = self.mock_project

    self.mock_job = mock.Mock(spec=dataproc.Job)
    self.mock_job.state = 'ERROR'
    self.mock_job.status_history = {'RUNNING': '2025-01-01T10:00:00.000Z'}
    self.mock_job.cluster_uuid = 'test-uuid'
    self.mock_job.cluster_name = 'test-cluster'
    self.mock_job.details = ''
    self.mock_job.job_provided_bq_connector = None
    self.mock_dataproc_get_job_by_jobid.return_value = self.mock_job

    self.mock_cluster = mock.Mock(spec=dataproc.Cluster)
    self.mock_cluster.vm_service_account_email = 'test-sa@example.com'
    self.mock_cluster.is_stackdriver_logging_enabled = True
    self.mock_cluster.image_version = '2.0.0-debian10'
    self.mock_cluster.autoscaling_policy_id = None
    self.mock_cluster.number_of_primary_workers = 2
    self.mock_cluster.number_of_secondary_workers = 0
    self.mock_cluster.is_preemptible_primary_workers = False
    self.mock_cluster.is_preemptible_secondary_workers = False
    self.mock_cluster.is_custom_gcs_connector = False
    self.mock_cluster.cluster_provided_bq_connector = None
    self.mock_cluster.config = mock.Mock()
    self.mock_cluster.config.software_config.properties = {}
    self.mock_cluster.config.worker_config.disk_config.boot_disk_size_gb = 500
    self.mock_cluster.config.software_config.image_version = '2.0.0-debian10'

    self.mock_dataproc_get_cluster.return_value = self.mock_cluster


class JobStartTest(SparkJobFailuresStepTestBase):

  def test_job_start_ok(self):
    step = spark_job_failures.JobStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dataproc_get_job_by_jobid.assert_called_once()
    self.mock_dataproc_get_cluster.assert_called_once()
    self.assertTrue(self.params['cluster_exists'])
    self.assertEqual(self.params[flags.SERVICE_ACCOUNT], 'test-sa@example.com')
    self.mock_interface.add_ok.assert_called_once()

  def test_job_start_done(self):
    self.mock_job.state = 'DONE'
    step = spark_job_failures.JobStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_start_api_error(self):
    self.mock_dataproc_get_job_by_jobid.side_effect = utils.GcpApiError(
        'api error')
    step = spark_job_failures.JobStart()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_older_than_30_days(self):
    self.mock_job.status_history = {'RUNNING': '2024-01-01T10:00:00.000Z'}
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.check_datetime_gap',
        return_value=True,
    ):
      step = spark_job_failures.JobStart()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      self.assertTrue(self.params[flags.JOB_OLDER_THAN_30_DAYS])


class JobDetailsDependencyGatewayTest(SparkJobFailuresStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.spark_job_failures.JobDetailsDependencyGateway.add_child'
        ))

  def test_cluster_exists(self):
    self.params['cluster_exists'] = True
    step = spark_job_failures.JobDetailsDependencyGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.add_child_patch.call_count, 19)

  def test_cluster_does_not_exist(self):
    self.params['cluster_exists'] = False
    step = spark_job_failures.JobDetailsDependencyGateway()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.add_child_patch.call_count, 14)


class CheckStackdriverSettingTest(SparkJobFailuresStepTestBase):

  def test_stackdriver_enabled(self):
    self.mock_cluster.is_stackdriver_logging_enabled = True
    step = spark_job_failures.CheckStackdriverSetting()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertTrue(self.params[flags.STACKDRIVER])
    self.mock_interface.add_ok.assert_called_once()

  def test_stackdriver_disabled(self):
    self.mock_cluster.is_stackdriver_logging_enabled = False
    step = spark_job_failures.CheckStackdriverSetting()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertFalse(self.params[flags.STACKDRIVER])
    self.mock_interface.add_uncertain.assert_called_once()

  def test_cluster_none(self):
    self.mock_dataproc_get_cluster.return_value = None
    step = spark_job_failures.CheckStackdriverSetting()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()


class CheckClusterVersionTest(SparkJobFailuresStepTestBase):

  def test_version_supported(self):
    self.mock_dp_extract_supported_version.return_value = ['2.0']
    self.mock_cluster.image_version = '2.0.1-debian10'
    step = spark_job_failures.CheckClusterVersion()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_version_not_supported(self):
    self.mock_dp_extract_supported_version.return_value = ['1.5']
    self.mock_cluster.image_version = '2.0.1-debian10'
    step = spark_job_failures.CheckClusterVersion()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()


class CheckTaskNotFoundTest(SparkJobFailuresStepTestBase):

  def test_job_older_than_30_days(self):
    self.params[flags.JOB_OLDER_THAN_30_DAYS] = True
    step = spark_job_failures.CheckTaskNotFound()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_job_not_task_not_found(self):
    self.mock_job.details = 'some other error'
    self.mock_logs_realtime_query.return_value = []
    step = spark_job_failures.CheckTaskNotFound()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_job_task_not_found_logs_found(self):
    self.mock_job.details = 'Task not found'
    self.mock_logs_realtime_query.return_value = [{
        'protoPayload': {
            'authenticationInfo': {
                'principalEmail': 'user@example.com'
            }
        }
    }]
    step = spark_job_failures.CheckTaskNotFound()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'User user@example.com deleted the cluster',
        self.mock_interface.add_failed.call_args[1]['reason'],
    )

  def test_job_task_not_found_logs_not_found(self):
    self.mock_job.details = 'Task not found'
    self.mock_logs_realtime_query.return_value = []
    step = spark_job_failures.CheckTaskNotFound()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'Unable to find the cluster deletion log',
        self.mock_interface.add_failed.call_args[1]['reason'],
    )


class CheckPermissionsTest(SparkJobFailuresStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.spark_job_failures.CheckPermissions.add_child'
        ))

  def test_no_sa(self):
    self.params[flags.SERVICE_ACCOUNT] = None
    step = spark_job_failures.CheckPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_sa_exists_same_project(self):
    self.params[flags.PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.SERVICE_ACCOUNT] = (
        'service-account-1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.side_effect = [True]
    step = spark_job_failures.CheckPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.add_child_patch.assert_called_once()
    self.assertIsInstance(self.add_child_patch.call_args[1]['child'],
                          iam_gs.IamPolicyCheck)

  def test_sa_exists_cross_project(self):
    self.params[flags.PROJECT_ID] = 'gcpdiag-dataproc1-aaaa'
    self.params[flags.CROSS_PROJECT_ID] = 'gcpdiag-iam1-aaaa'
    self.params[flags.SERVICE_ACCOUNT] = (
        'service-account-1@gcpdiag-iam1-aaaa.iam.gserviceaccount.com')
    self.mock_iam_is_service_account_existing.side_effect = [False, True]
    step = spark_job_failures.CheckPermissions()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.add_child_patch.call_count, 4)


class CheckMasterOOMTest(SparkJobFailuresStepTestBase):

  def test_no_task_not_acquired(self):
    self.mock_logs_realtime_query.return_value = []
    step = spark_job_failures.CheckMasterOOM()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_task_not_acquired_sigterm(self):
    self.mock_logs_realtime_query.side_effect = [
        [{
            'log': 'task not acquired'
        }],
        [{
            'log': 'sigterm'
        }],
    ]
    step = spark_job_failures.CheckMasterOOM()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_task_not_acquired_yarn_metrics(self):
    self.mock_logs_realtime_query.side_effect = [
        [{
            'log': 'task not acquired'
        }],
        [],
        [{
            'log': 'yarn metrics'
        }],
    ]
    step = spark_job_failures.CheckMasterOOM()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()


class CheckCompositeStepTest(SparkJobFailuresStepTestBase):

  def test_check_worker_oom(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckWorkerOOM.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckWorkerOOM()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_sw_preemption(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckSWPreemption.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckSWPreemption()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_worker_disk_usage_issue(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckWorkerDiskUsageIssue.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckWorkerDiskUsageIssue()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_port_exhaustion(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckPortExhaustion.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckPortExhaustion()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_killing_orphaned_application(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckKillingOrphanedApplication.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckKillingOrphanedApplication()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_python_import_failure(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckPythonImportFailure.add_child'
    ) as mock_add_child:
      self.mock_cluster.initialization_actions = True
      step = spark_job_failures.CheckPythonImportFailure()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)
      self.mock_interface.info.assert_called_once()

  def test_check_gc_pause(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckGCPause.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckGCPause()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)

  def test_check_job_throttling(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckJobThrottling.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckJobThrottling()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      self.assertEqual(mock_add_child.call_count, 6)

  def test_check_yarn_runtime_exception(self):
    with mock.patch(
        'gcpdiag.runbook.dataproc.spark_job_failures.CheckYarnRuntimeException.add_child'
    ) as mock_add_child:
      step = spark_job_failures.CheckYarnRuntimeException()
      with op.operator_context(self.operator):
        self.operator.set_step(step)
        step.execute()
      mock_add_child.assert_called_once()
      self.assertIsInstance(mock_add_child.call_args[1]['child'],
                            dp_gs.CheckLogsExist)


class CheckShuffleFailuresTest(SparkJobFailuresStepTestBase):

  def test_job_older_than_30_days(self):
    self.params[flags.JOB_OLDER_THAN_30_DAYS] = True
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()

  def test_no_logs(self):
    self.mock_logs_realtime_query.return_value = []
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_logs_found_efm_workers(self):
    self.mock_logs_realtime_query.return_value = [{'log': 'shuffle fail'}]
    self.mock_cluster.config.software_config.properties = {
        'dataproc:dataproc.enable.enhanced.flexibility.mode': 'true'
    }
    self.mock_cluster.number_of_primary_workers = 1
    self.mock_cluster.number_of_secondary_workers = 2
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'Insufficient primary workers',
        self.mock_interface.add_failed.call_args[1]['reason'],
    )

  def test_logs_found_old_image(self):
    self.mock_logs_realtime_query.return_value = [{'log': 'shuffle fail'}]
    self.mock_cluster.config.software_config.image_version = '1.5.0'
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'Consider using EFM HCFS mode',
        self.mock_interface.add_failed.call_args[1]['remediation'],
    )

  def test_logs_found_small_disk(self):
    self.mock_logs_realtime_query.return_value = [{'log': 'shuffle fail'}]
    self.mock_cluster.config.worker_config.disk_config.boot_disk_size_gb = 100
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn('Small disk size',
                  self.mock_interface.add_failed.call_args[1]['reason'])

  def test_logs_found_low_timeout(self):
    self.mock_logs_realtime_query.return_value = [{'log': 'shuffle fail'}]
    self.mock_cluster.config.software_config.properties = {
        'spark:spark.shuffle.io.connectionTimeout': 50
    }
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'Low IO connection timeout',
        self.mock_interface.add_failed.call_args[1]['reason'],
    )

  def test_logs_found_pvm(self):
    self.mock_logs_realtime_query.return_value = [{'log': 'shuffle fail'}]
    self.mock_cluster.is_preemptible_secondary_workers = True
    step = spark_job_failures.CheckShuffleFailures()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()
    self.assertIn(
        'Data skew and large partitions',
        self.mock_interface.add_failed.call_args[1]['reason'],
    )


class CheckShuffleServiceKillTest(SparkJobFailuresStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.spark_job_failures.CheckShuffleServiceKill.add_child'
        ))

  def test_add_child_called(self):
    step = spark_job_failures.CheckShuffleServiceKill()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.assertEqual(self.add_child_patch.call_count, 2)
    self.assertIsInstance(self.add_child_patch.call_args_list[0][1]['child'],
                          dp_gs.CheckLogsExist)
    self.assertIsInstance(
        self.add_child_patch.call_args_list[1][1]['child'],
        spark_job_failures.CheckAutoscalingPolicy,
    )


class CheckAutoscalingPolicyTest(SparkJobFailuresStepTestBase):

  def test_no_policy(self):
    self.mock_cluster.autoscaling_policy_id = None
    step = spark_job_failures.CheckAutoscalingPolicy()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_dp_get_autoscaling_policy.assert_not_called()

  def test_policy_no_graceful_timeout(self):
    self.mock_cluster.autoscaling_policy_id = 'test-policy'
    mock_policy = mock.Mock()
    mock_policy.has_graceful_decommission_timeout = False
    self.mock_dp_get_autoscaling_policy.return_value = mock_policy
    step = spark_job_failures.CheckAutoscalingPolicy()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_policy_with_graceful_timeout(self):
    self.mock_cluster.autoscaling_policy_id = 'test-policy'
    mock_policy = mock.Mock()
    mock_policy.has_graceful_decommission_timeout = True
    self.mock_dp_get_autoscaling_policy.return_value = mock_policy
    step = spark_job_failures.CheckAutoscalingPolicy()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()


class CheckPreemptibleTest(SparkJobFailuresStepTestBase):

  def test_preemptible_workers_high_ratio(self):
    self.mock_cluster.is_preemptible_secondary_workers = True
    self.mock_cluster.number_of_secondary_workers = 5
    self.mock_cluster.number_of_primary_workers = 5
    step = spark_job_failures.CheckPreemptible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_failed.assert_called_once()

  def test_preemptible_workers_low_ratio(self):
    self.mock_cluster.is_preemptible_secondary_workers = True
    self.mock_cluster.number_of_secondary_workers = 1
    self.mock_cluster.number_of_primary_workers = 5
    step = spark_job_failures.CheckPreemptible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_no_preemptible_workers(self):
    step = spark_job_failures.CheckPreemptible()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_not_called()
    self.mock_interface.add_failed.assert_not_called()


class CheckGCSConnectorTest(SparkJobFailuresStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.spark_job_failures.CheckGCSConnector.add_child'
        ))

  def test_custom_connector(self):
    self.mock_cluster.is_custom_gcs_connector = True
    step = spark_job_failures.CheckGCSConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()
    self.assertEqual(self.add_child_patch.call_count, 4)

  def test_default_connector(self):
    self.mock_cluster.is_custom_gcs_connector = False
    step = spark_job_failures.CheckGCSConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()
    self.assertEqual(self.add_child_patch.call_count, 4)


class CheckBQConnectorTest(SparkJobFailuresStepTestBase):

  def setUp(self):
    super().setUp()
    self.add_child_patch = self.enterContext(
        mock.patch(
            'gcpdiag.runbook.dataproc.spark_job_failures.CheckBQConnector.add_child'
        ))
    self.params['image_version'] = '2.1.0'
    self.mock_dp_extract_bq_version.return_value = '0.28.0'

  def test_cluster_none(self):
    self.mock_dataproc_get_cluster.return_value = None
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()
    self.add_child_patch.assert_called_once()

  def test_version_ok_no_connector(self):
    self.params['image_version'] = '2.1.0'
    self.mock_cluster.cluster_provided_bq_connector = None
    self.mock_job.job_provided_bq_connector = None
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_version_uncertain_job_connector_mismatch(self):
    self.params['image_version'] = '2.1.0'
    self.mock_cluster.cluster_provided_bq_connector = None
    self.mock_job.job_provided_bq_connector = '0.27.0'
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_version_uncertain_cluster_connector_mismatch(self):
    self.params['image_version'] = '2.1.0'
    self.mock_cluster.cluster_provided_bq_connector = '0.27.0'
    self.mock_job.job_provided_bq_connector = None
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_uncertain.assert_called_once()

  def test_version_ok_old_image_with_connector(self):
    self.params['image_version'] = '1.5.0'
    self.mock_cluster.image_version = '1.5.0'
    type(self.mock_cluster).cluster_provided_bq_connector = mock.PropertyMock(
        return_value='some-connector')
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_ok.assert_called_once()

  def test_version_skipped_old_image_no_connector(self):
    self.params['image_version'] = '1.5.0'
    self.mock_cluster.image_version = '1.5.0'
    self.mock_cluster.cluster_provided_bq_connector = None
    self.mock_job.job_provided_bq_connector = None
    step = spark_job_failures.CheckBQConnector()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.add_skipped.assert_called_once()


class SparkJobEndTest(SparkJobFailuresStepTestBase):

  def test_end_step(self):
    step = spark_job_failures.SparkJobEnd()
    with op.operator_context(self.operator):
      self.operator.set_step(step)
      step.execute()
    self.mock_interface.info.assert_called_once()


if __name__ == '__main__':
  unittest.main()
