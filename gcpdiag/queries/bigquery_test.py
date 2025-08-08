"""Tests for code in bigquery.py."""

from unittest import mock

import pytest

from gcpdiag import caching
from gcpdiag.queries import apis, apis_stub, bigquery
from gcpdiag.queries.bigquery import C_NOT_AVAILABLE, BigQueryJob
from gcpdiag.runbook.op_test import with_operator_context
from gcpdiag.utils import GcpApiError

DUMMY_PROJECT_ID = 'gcpdiag-bigquery1-aaaa'
DUMMY_REGION = 'us'
DUMMY_JOB_ID = 'job1'
DUMMY_JOB_ID_2 = 'job2'
DUMMY_JOB_ID_I_S = 'information_schema_job1'
DUMMY_JOB_ID_FAIL = 'job_not_found'
DUMMY_JOB_FULL_ID = f'{DUMMY_PROJECT_ID}:{DUMMY_REGION.upper()}.{DUMMY_JOB_ID}'
DUMMY_JOB_FULL_ID_2 = (
    f'{DUMMY_PROJECT_ID}:{DUMMY_REGION.upper()}.{DUMMY_JOB_ID_2}')
DUMMY_PRINCIPAL = 'user:test@example.com'
DUMMY_ORG_ID = '123456789012'
DUMMY_QUERY = (
    'NOT BEING EXECUTED (SELECT col1, col2 FROM my_dataset.my_table LIMIT 2)')
DUMMY_UUID = 'mockresult1'  # Corresponds to the results file name


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestBigQueryQueries:
  """Test BigQuery queries."""

  @with_operator_context
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  def test_get_bigquery_job1_success_and_properties(self, mock_api_is_enabled,
                                                    mock_get_user_email):
    # Test creating BigQueryJob object successfully for job1 and check
    # properties.
    del mock_api_is_enabled
    del mock_get_user_email
    job = bigquery.get_bigquery_job(DUMMY_PROJECT_ID, DUMMY_REGION.upper(),
                                    DUMMY_JOB_ID)
    assert isinstance(job, BigQueryJob)
    assert job.project_id == DUMMY_PROJECT_ID
    assert job.id == DUMMY_JOB_FULL_ID
    # TOmarcialrDO: does not make much sense since models.py makes short_path
    # == fullpath
    # assert job.short_path == f'{DUMMY_PROJECT_ID}/{DUMMY_REGION.upper()}/
    # {DUMMY_JOB_ID}'
    assert job.full_path.endswith(
        f'/jobs/{DUMMY_JOB_ID}?location={DUMMY_REGION.upper()}')
    assert job.user_email is not None
    assert job.query_sql is not None
    assert job.creation_time is not None
    assert isinstance(job.total_bytes_billed, int)
    assert isinstance(job.cache_hit, bool)
    assert job.job_state == 'DONE'
    # TOmarcialrDO: information_schema query not implemented yet
    # assert job.information_schema_user_email is not None
    # assert job.information_schema_start_time_str is not None
    # assert job.information_schema_end_time_str is not None
    # assert job.information_schema_query is not None

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.bigquery.uuid.uuid4', return_value=DUMMY_UUID)
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  def test_get_query_results_success(self, mock_api_is_enabled, mock_uuid,
                                     mock_get_user_email):
    # Test get_query_results successfully executes and returns rows.
    del mock_api_is_enabled
    del mock_uuid
    del mock_get_user_email
    results = bigquery.get_query_results(
        project_id=DUMMY_PROJECT_ID,
        query=DUMMY_QUERY,
        location=DUMMY_REGION,  # Use 'us'
        timeout_sec=10,  # Short timeout for test
        poll_interval_sec=1,  # Short poll interval
    )
    assert results is not None
    assert isinstance(results, list)
    assert len(results) == 2
    # Note: BQ returns strings for INTs via JSON API, handle potential type
    # conversion if needed
    assert results[0] == {'col1': 'value1', 'col2': '100'}
    assert results[1] == {'col1': 'value2', 'col2': '200'}

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=False)
  def test_get_query_results_api_disabled(self, mock_api_is_enabled,
                                          mock_get_user_email):
    # Test get_query_results returns None when API is disabled
    del mock_get_user_email
    results = bigquery.get_query_results(project_id=DUMMY_PROJECT_ID,
                                         query=DUMMY_QUERY,
                                         location=DUMMY_REGION)
    assert results is None
    mock_api_is_enabled.assert_called_once_with(DUMMY_PROJECT_ID, 'bigquery')

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  def test_get_bigquery_job2_success(self, mock_api_is_enabled,
                                     mock_get_user_email):
    # Test creating BigQueryJob object successfully for job2.
    del mock_api_is_enabled
    del mock_get_user_email
    job = bigquery.get_bigquery_job(DUMMY_PROJECT_ID, DUMMY_REGION.upper(),
                                    DUMMY_JOB_ID_2)
    assert isinstance(job, BigQueryJob)
    assert job.project_id == DUMMY_PROJECT_ID
    assert job.id == DUMMY_JOB_FULL_ID_2
    assert job.job_state == 'DONE'
    # TOmarcialrDO: alihanoz
    # assert job.job_error_result == {}
    # assert job.job_errors == []
    # Add more assertions based on job2 data (e.g., check billing > 0)
    assert job.total_bytes_billed >= 0

  def test_get_bigquery_job_returns_none_on_api_fail(self):
    """Test get_bigquery_job returns None if the underlying jobs.get call fails."""
    job = bigquery.get_bigquery_job(DUMMY_PROJECT_ID, DUMMY_REGION.upper(),
                                    DUMMY_JOB_ID_FAIL)
    assert job is None

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  def test_get_info_schema_not_found_returns_none(self, mock_get_user_email):
    """Verify get_information_schema_job_metadata returns None when query finds no match."""
    del mock_get_user_email
    result = bigquery.get_information_schema_job_metadata(
        DUMMY_PROJECT_ID, DUMMY_REGION.upper(), DUMMY_JOB_ID_FAIL)
    assert result is None

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=False)
  def test_get_info_schema_api_disabled(self, mock_api_is_enabled,
                                        mock_get_user_email):
    """Test jobs.query returning None when API is disabled."""
    del mock_get_user_email
    del mock_api_is_enabled
    result = bigquery.get_information_schema_job_metadata(
        DUMMY_PROJECT_ID, DUMMY_REGION.upper(), DUMMY_JOB_ID)
    assert result is None

  @with_operator_context
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  def test_get_bigquery_job_info_schema_fails(self, mock_api_is_enabled,
                                              mock_get_user_email):
    # While testing, we cannot retrieve IS job so it behaves
    # like an error happened when querying I_S so
    # job._information_schema_job_metadata = {}
    del mock_get_user_email
    del mock_api_is_enabled
    with caching.bypass_cache():
      job = bigquery.get_bigquery_job(DUMMY_PROJECT_ID, DUMMY_REGION.upper(),
                                      DUMMY_JOB_ID)
    assert isinstance(job, BigQueryJob)
    assert job.id == DUMMY_JOB_FULL_ID
    assert job.information_schema_user_email is C_NOT_AVAILABLE
    assert job.information_schema_start_time_str is C_NOT_AVAILABLE
    assert job.information_schema_end_time_str is C_NOT_AVAILABLE
    assert job.information_schema_query is C_NOT_AVAILABLE

  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  def test_get_job_api_data_not_found_raises_error(self, mock_api_is_enabled,
                                                   mock_get_user_email):
    # Verify get_bigquery_job_api_resource_data raises GcpApiError on 404.
    del mock_api_is_enabled
    del mock_get_user_email
    with caching.bypass_cache():
      with pytest.raises(GcpApiError):
        bigquery.get_bigquery_job_api_resource_data(DUMMY_PROJECT_ID,
                                                    DUMMY_REGION.upper(),
                                                    DUMMY_JOB_ID_FAIL)

  @with_operator_context
  @mock.patch('gcpdiag.queries.apis.is_enabled', return_value=True)
  @mock.patch.object(apis,
                     'get_user_email',
                     return_value='testuser@example.com')
  def test_get_bigquery_job_info_schema_extended_fields_fail(
      self, mock_api_is_enabled, mock_get_user_email):
    # Test get_bigquery_job returns CONST_NOT_AVAILABLE for extended info
    # schema fields when the underlying query for metadata fails.
    # We actually do not have a working underlying query
    del mock_api_is_enabled
    del mock_get_user_email
    with caching.bypass_cache():
      job = bigquery.get_bigquery_job(DUMMY_PROJECT_ID, DUMMY_REGION.upper(),
                                      DUMMY_JOB_ID)
    assert isinstance(job, BigQueryJob)
    assert job.id == DUMMY_JOB_FULL_ID
    assert job.information_schema_total_modified_partitions == C_NOT_AVAILABLE
    assert job.information_schema_resource_warning == C_NOT_AVAILABLE
    assert job.information_schema_normalized_literals == C_NOT_AVAILABLE
