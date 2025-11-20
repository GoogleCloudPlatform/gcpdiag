"""Queries related to BigQuery."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Set, Union

from google.auth import exceptions
from googleapiclient import errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, crm, iam
from gcpdiag.runbook import op

BIGQUERY_REGIONS = [
    'me-central1',
    'me-central2',
    'me-west1',
    'africa-south1',
    'us',
    'eu',
    'us-east1',
    'us-east4',
    'us-east5',
    'us-west1',
    'us-west2',
    'us-west3',
    'us-west4',
    'us-central1',
    'us-south1',
    'northamerica-northeast1',
    'northamerica-northeast2',
    'southamerica-east1',
    'southamerica-west1',
    'asia-east1',
    'asia-east2',
    'asia-south1',
    'asia-south2',
    'asia-northeast1',
    'asia-northeast2',
    'asia-northeast3',
    'asia-southeast1',
    'asia-southeast2',
    'australia-southeast1',
    'australia-southeast2',
    'europe-north1',
    'europe-southwest1',
    'europe-central2',
    'europe-west1',
    'europe-west10',
    'europe-west2',
    'europe-west3',
    'europe-west4',
    'europe-west6',
    'europe-west8',
    'europe-west9',
    'europe-west12',
]
# STRING CONSTANTS
C_NOT_AVAILABLE = 'N/A'

PolicyObject = Union[iam.ProjectPolicy, iam.OrganizationPolicy]


def get_project_policy(context: models.Context):
  """Fetches the IAM policy object for a project."""
  root_logger = logging.getLogger()
  original_level = root_logger.level

  try:
    root_logger.setLevel(logging.ERROR)
    policy = iam.get_project_policy(context, raise_error_if_fails=False)
    return policy
  except utils.GcpApiError:
    return None
  finally:
    root_logger.setLevel(original_level)


def get_organization_policy(context: models.Context, organization_id: str):
  """Fetches the IAM policy object for an organization."""
  root_logger = logging.getLogger()
  original_level = root_logger.level

  try:
    root_logger.setLevel(logging.ERROR)
    policy = iam.get_organization_policy(context,
                                         organization_id,
                                         raise_error_if_fails=False)
    return policy
  except utils.GcpApiError as err:
    if 'doesn\'t have access to' in err.message.lower(
    ) or 'denied on resource' in err.message.lower():
      op.info(
          'User does not have access to the organization policy. Investigation'
          ' completeness and accuracy might depend on the presence of'
          ' organization level permissions.')
    return None
  finally:
    root_logger.setLevel(original_level)


def check_permissions_for_principal(
    policy: PolicyObject, principal: str,
    permissions_to_check: Set[str]) -> Dict[str, bool]:
  """Uses a policy object to check a set of permissions for a principal.

  Returns a dictionary mapping each permission to a boolean indicating its
  presence.
  """
  return {
      permission: policy.has_permission(principal, permission)
      for permission in permissions_to_check
  }


def get_missing_permissions(required_permissions: Set[str],
                            actual_permissions: Dict[str, bool]) -> Set[str]:
  """Compares a set of required permissions against a dictionary of actual

  permissions and returns the set of missing ones.
  """
  return {
      perm for perm in required_permissions if not actual_permissions.get(perm)
  }


class BigQueryTable:
  """Represents a BigQuery Table object."""

  project_id: str
  dataset_id: str
  table_id: str

  def __init__(self, project_id: str, dataset_id: str, table_id: str):
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.table_id = table_id

  @property
  def table_identifier(self) -> str:
    return f'{self.project_id}:{self.dataset_id}.{self.table_id}'


class BigQueryRoutine:
  """Represents a BigQuery Routine object."""

  project_id: str
  dataset_id: str
  routine_id: str

  def __init__(self, project_id: str, dataset_id: str, routine_id: str):
    self.project_id = project_id
    self.dataset_id = dataset_id
    self.routine_id = routine_id

  @property
  def routine_identifier(self) -> str:
    return f'{self.project_id}:{self.dataset_id}.{self.routine_id}'


class BigQueryJob(models.Resource):
  """Represents a BigQuery Job object."""

  _job_api_resource_data: dict[str, Any]
  _information_schema_job_metadata: dict[str, Any]
  project_id: str

  def __init__(
      self,
      project_id: str,
      job_api_resource_data: dict[str, Any],
      information_schema_job_metadata: dict[str, str],
  ):
    super().__init__(project_id)
    self._job_api_resource_data = job_api_resource_data
    self._information_schema_job_metadata = (information_schema_job_metadata or
                                             {})

  @property
  def full_path(self) -> str:
    # returns 'https://content-bigquery.googleapis.com/bigquery/v2/
    # projects/<PROJECT_ID>/jobs/<JOBID>?location=<REGION>'
    return self._job_api_resource_data.get('selfLink', '')

  @property
  def id(self) -> str:
    # returns <PROJECT>:<REGION>.<JobID>
    return self._job_api_resource_data.get('id', '')

  @property
  def short_path(self) -> str:
    # returns <PROJECT>:<REGION>.<JobID>
    return self.id

  @property
  def user_email(self) -> str:
    return self._job_api_resource_data.get('user_email', '')

  @property
  def _job_configuration(self) -> dict[str, Any]:
    return self._job_api_resource_data.get('configuration', {})

  @property
  def _query(self) -> dict[str, Any]:
    return self._job_configuration.get('query', {})

  @property
  def _stats(self) -> dict[str, Any]:
    """Safely access the 'statistics' dictionary."""
    return self._job_api_resource_data.get('statistics', {})

  @property
  def _query_stats(self) -> dict[str, Any]:
    """Safely access the 'statistics.query' dictionary."""
    return self._stats.get('query', {})

  @property
  def _query_info(self) -> dict[str, Any]:
    return self._query_stats.get('queryInfo', {})

  @property
  def _status(self) -> dict[str, Any]:
    return self._job_api_resource_data.get('status', {})

  @property
  def job_type(self) -> str:
    return self._job_configuration.get('jobType', '')

  @property
  def query_sql(self) -> str:
    return self._query.get('query', '')

  @property
  def use_legacy_sql(self) -> bool:
    return self._query.get('useLegacySql', False)

  @property
  def priority(self) -> str:
    return self._query.get('priority', '')

  @property
  def edition(self) -> str:
    edition_value = self._query.get('edition')
    return str(edition_value) if edition_value else ''

  @property
  def creation_time(self) -> Optional[int]:
    time_str = self._stats.get('creationTime')
    return (int(time_str)
            if isinstance(time_str, str) and time_str.isdigit() else None)

  @property
  def start_time(self) -> Optional[int]:
    time_str = self._stats.get('startTime')
    return (int(time_str)
            if isinstance(time_str, str) and time_str.isdigit() else None)

  @property
  def end_time(self) -> Optional[int]:
    time_str = self._stats.get('endTime')
    return (int(time_str)
            if isinstance(time_str, str) and time_str.isdigit() else None)

  @property
  def total_bytes_processed(self) -> int:
    bytes_str = self._stats.get('totalBytesProcessed', '0')
    return (int(bytes_str)
            if isinstance(bytes_str, str) and bytes_str.isdigit() else 0)

  @property
  def total_bytes_billed(self) -> int:
    bytes_str = self._query_stats.get('totalBytesBilled', '0')
    return (int(bytes_str)
            if isinstance(bytes_str, str) and bytes_str.isdigit() else 0)

  @property
  def total_slot_ms(self) -> int:
    ms_str = self._stats.get('totalSlotMs', '0')
    return int(ms_str) if isinstance(ms_str, str) and ms_str.isdigit() else 0

  @property
  def cache_hit(self) -> bool:
    return self._query_stats.get('cacheHit') is True

  @property
  def quota_deferments(self) -> list[str]:
    deferments_dict = self._stats.get('quotaDeferments', {})
    if isinstance(deferments_dict, dict):
      deferment_list = deferments_dict.get('', [])
      if isinstance(deferment_list, list) and all(
          isinstance(s, str) for s in deferment_list):
        return deferment_list
    return []

  @property
  def query_plan(self) -> list[dict[str, Any]]:
    plan = self._query_stats.get('queryPlan', [])
    return plan if isinstance(plan, list) else []

  @property
  def total_partitions_processed(self) -> int:
    partitions_str = self._query_stats.get('totalPartitionsProcessed', '0')
    return (int(partitions_str) if isinstance(partitions_str, str) and
            partitions_str.isdigit() else 0)

  @property
  def referenced_tables(self) -> list[BigQueryTable]:
    tables_list = self._query_stats.get('referencedTables', [])
    referenced_tables = []
    if isinstance(tables_list, list):
      for item in tables_list:
        if isinstance(item, dict):
          project_id = item.get('projectId')
          dataset_id = item.get('datasetId')
          table_id = item.get('tableId')
          if (isinstance(project_id, str) and project_id and
              isinstance(dataset_id, str) and dataset_id and
              isinstance(table_id, str) and table_id):
            referenced_tables.append(
                BigQueryTable(project_id, dataset_id, table_id))
    return referenced_tables

  @property
  def referenced_routines(self) -> list[BigQueryRoutine]:
    routines_list = self._query_stats.get('referencedRoutines', [])
    referenced_routines = []
    if isinstance(routines_list, list):
      for item in routines_list:
        if isinstance(item, dict):
          project_id = item.get('projectId')
          dataset_id = item.get('datasetId')
          routine_id = item.get('routineId')
          if (isinstance(project_id, str) and project_id and
              isinstance(dataset_id, str) and dataset_id and
              isinstance(routine_id, str) and routine_id):
            referenced_routines.append(
                BigQueryRoutine(project_id, dataset_id, routine_id))
    return referenced_routines

  @property
  def num_affected_dml_rows(self) -> int:
    rows_str = self._query_stats.get('numDmlAffectedRows', '0')
    return (int(rows_str)
            if isinstance(rows_str, str) and rows_str.isdigit() else 0)

  @property
  def dml_stats(self) -> dict[str, int]:
    stats = self._query_stats.get('dmlStats')
    if not isinstance(stats, dict):
      return {}
    inserted_str = stats.get('insertedRowCount', '0')
    deleted_str = stats.get('deletedRowCount', '0')
    updated_str = stats.get('updatedRowCount', '0')
    return {
        'insertedRowCount':
            (int(inserted_str) if isinstance(inserted_str, str) and
             inserted_str.isdigit() else 0),
        'deletedRowCount': (int(deleted_str) if isinstance(deleted_str, str) and
                            deleted_str.isdigit() else 0),
        'updatedRowCount': (int(updated_str) if isinstance(updated_str, str) and
                            updated_str.isdigit() else 0),
    }

  @property
  def statement_type(self) -> str:
    stype = self._query_stats.get('statementType', '')
    return stype if isinstance(stype, str) else ''

  @property
  def bi_engine_statistics(self) -> dict[str, Any]:
    stats = self._query_stats.get('biEngineStatistics')
    if not isinstance(stats, dict):
      return {}
    reasons_list = stats.get('accelerationMode', {}).get('biEngineReasons', [])
    bi_engine_reasons = []
    if isinstance(reasons_list, list):
      for item in reasons_list:
        if isinstance(item, dict):
          bi_engine_reasons.append({
              'code': str(item.get('code', '')),
              'message': item.get('message', ''),
          })
    return {
        'biEngineMode': str(stats.get('biEngineMode', '')),
        'accelerationMode': str(stats.get('accelerationMode', '')),
        'biEngineReasons': bi_engine_reasons,
    }

  @property
  def vector_search_statistics(self) -> dict[str, Any]:
    stats = self._query_stats.get('vectorSearchStatistics')
    if not isinstance(stats, dict):
      return {}
    reasons_list = stats.get('indexUnusedReasons', [])
    index_unused_reasons = []
    if isinstance(reasons_list, list):
      for item in reasons_list:
        if isinstance(item, dict):
          base_table_data = item.get('baseTable')
          base_table_obj = None
          if isinstance(base_table_data, dict):
            project_id = base_table_data.get('projectId')
            dataset_id = base_table_data.get('datasetId')
            table_id = base_table_data.get('tableId')
            if (isinstance(project_id, str) and project_id and
                isinstance(dataset_id, str) and dataset_id and
                isinstance(table_id, str) and table_id):
              base_table_obj = BigQueryTable(project_id, dataset_id, table_id)
          index_unused_reasons.append({
              'code': str(item.get('code', '')),
              'message': item.get('message', ''),
              'indexName': item.get('indexName', ''),
              'baseTable': base_table_obj,
          })
    return {
        'indexUsageMode': str(stats.get('indexUsageMode', '')),
        'indexUnusedReasons': index_unused_reasons,
    }

  @property
  def performance_insights(self) -> dict[str, Any]:
    insights = self._query_stats.get('performanceInsights')
    if not isinstance(insights, dict):
      return {}
    standalone_list = insights.get('stagePerformanceStandaloneInsights', [])
    stage_performance_standalone_insights = []
    if isinstance(standalone_list, list):
      for item in standalone_list:
        if isinstance(item, dict):
          stage_performance_standalone_insights.append({
              'stageId': item.get('stageId', ''),
          })
    change_list = insights.get('stagePerformanceChangeInsights', [])
    stage_performance_change_insights = []
    if isinstance(change_list, list):
      for item in change_list:
        if isinstance(item, dict):
          stage_performance_change_insights.append({
              'stageId': item.get('stageId', ''),
          })
    avg_ms_str = insights.get('avgPreviousExecutionMs', '0')
    return {
        'avgPreviousExecutionMs':
            (int(avg_ms_str)
             if isinstance(avg_ms_str, str) and avg_ms_str.isdigit() else 0),
        'stagePerformanceStandaloneInsights':
            (stage_performance_standalone_insights),
        'stagePerformanceChangeInsights': stage_performance_change_insights,
    }

  @property
  def optimization_details(self) -> Any:
    return self._query_info.get('optimizationDetails')

  @property
  def export_data_statistics(self) -> dict[str, int]:
    stats = self._query_stats.get('exportDataStatistics')
    if not isinstance(stats, dict):
      return {}
    file_count_str = stats.get('fileCount', '0')
    row_count_str = stats.get('rowCount', '0')
    return {
        'fileCount': (int(file_count_str) if isinstance(file_count_str, str) and
                      file_count_str.isdigit() else 0),
        'rowCount': (int(row_count_str) if isinstance(row_count_str, str) and
                     row_count_str.isdigit() else 0),
    }

  @property
  def load_query_statistics(self) -> dict[str, int]:
    stats = self._query_stats.get('loadQueryStatistics')
    if not isinstance(stats, dict):
      return {}
    input_files_str = stats.get('inputFiles', '0')
    input_bytes_str = stats.get('inputFileBytes', '0')
    output_rows_str = stats.get('outputRows', '0')
    output_bytes_str = stats.get('outputBytes', '0')
    bad_records_str = stats.get('badRecords', '0')
    return {
        'inputFiles':
            (int(input_files_str) if isinstance(input_files_str, str) and
             input_files_str.isdigit() else 0),
        'inputFileBytes':
            (int(input_bytes_str) if isinstance(input_bytes_str, str) and
             input_bytes_str.isdigit() else 0),
        'outputRows':
            (int(output_rows_str) if isinstance(output_rows_str, str) and
             output_rows_str.isdigit() else 0),
        'outputBytes':
            (int(output_bytes_str) if isinstance(output_bytes_str, str) and
             output_bytes_str.isdigit() else 0),
        'badRecords':
            (int(bad_records_str) if isinstance(bad_records_str, str) and
             bad_records_str.isdigit() else 0),
    }

  @property
  def spark_statistics(self) -> dict[str, Any]:
    stats = self._query_stats.get('sparkStatistics')
    if not isinstance(stats, dict):
      return {}
    logging_info_dict = stats.get('loggingInfo', {})
    logging_info = ({
        'resourceType': logging_info_dict.get('resourceType', ''),
        'projectId': logging_info_dict.get('projectId', ''),
    } if isinstance(logging_info_dict, dict) else {})
    return {
        'endpoints': stats.get('endpoints', {}),
        'sparkJobId': stats.get('sparkJobId', ''),
        'sparkJobLocation': stats.get('sparkJobLocation', ''),
        'kmsKeyName': stats.get('kmsKeyName', ''),
        'gcsStagingBucket': stats.get('gcsStagingBucket', ''),
        'loggingInfo': logging_info,
    }

  @property
  def transferred_bytes(self) -> int:
    bytes_str = self._query_stats.get('transferredBytes', '0')
    return (int(bytes_str)
            if isinstance(bytes_str, str) and bytes_str.isdigit() else 0)

  @property
  def reservation_id(self) -> str:
    res_id = self._stats.get('reservation_id', '')
    return res_id if isinstance(res_id, str) else ''

  @property
  def reservation_admin_project_id(self) -> Optional[str]:
    if not self.reservation_id:
      return None
    try:
      parts = self.reservation_id.split('/')
      if parts[0] == 'projects' and len(parts) >= 2:
        return parts[1]
      else:
        logging.warning(
            'Could not parse project ID from reservation_id: %s',
            self.reservation_id,
        )
        return None
    except (IndexError, AttributeError):
      logging.warning(
          'Could not parse project ID from reservation_id: %s',
          self.reservation_id,
      )
      return None

  @property
  def num_child_jobs(self) -> int:
    num_str = self._stats.get('numChildJobs', '0')
    return int(num_str) if isinstance(num_str, str) and num_str.isdigit() else 0

  @property
  def parent_job_id(self) -> str:
    parent_id = self._stats.get('parentJobId', '')
    return parent_id if isinstance(parent_id, str) else ''

  @property
  def row_level_security_applied(self) -> bool:
    rls_stats = self._stats.get('RowLevelSecurityStatistics', {})
    return (rls_stats.get('rowLevelSecurityApplied') is True if isinstance(
        rls_stats, dict) else False)

  @property
  def data_masking_applied(self) -> bool:
    masking_stats = self._stats.get('dataMaskingStatistics', {})
    return (masking_stats.get('dataMaskingApplied') is True if isinstance(
        masking_stats, dict) else False)

  @property
  def session_id(self) -> str:
    session_info = self._stats.get('sessionInfo', {})
    session_id_val = (session_info.get('sessionId', '') if isinstance(
        session_info, dict) else '')
    return session_id_val if isinstance(session_id_val, str) else ''

  @property
  def final_execution_duration_ms(self) -> int:
    duration_str = self._stats.get('finalExecutionDurationMs', '0')
    return (int(duration_str)
            if isinstance(duration_str, str) and duration_str.isdigit() else 0)

  @property
  def job_state(self) -> str:
    state = self._status.get('state', '')
    return state if isinstance(state, str) else ''

  @property
  def job_error_result(self) -> dict[str, Optional[str]]:
    error_result = self._status.get('errorResult')
    if not isinstance(error_result, dict):
      return {}
    return {
        'reason': error_result.get('reason'),
        'location': error_result.get('location'),
        'debugInfo': error_result.get('debugInfo'),
        'message': error_result.get('message'),
    }

  @property
  def job_errors(self) -> list[dict[str, Optional[str]]]:
    errors_list = self._status.get('errors', [])
    errors_iterable = []
    if isinstance(errors_list, list):
      for item in errors_list:
        if isinstance(item, dict):
          errors_iterable.append({
              'reason': item.get('reason'),
              'location': item.get('location'),
              'debugInfo': item.get('debugInfo'),
              'message': item.get('message'),
          })
    return errors_iterable

  @property
  def materialized_view_statistics(self) -> dict[str, Any]:
    stats_list = self._query_stats.get('materializedViewStatistics')
    materialized_view = []
    if isinstance(stats_list, list):
      for item in stats_list:
        if isinstance(item, dict):
          table_ref_data = item.get('tableReference')
          table_ref_obj = None
          if isinstance(table_ref_data, dict):
            project_id = table_ref_data.get('projectId')
            dataset_id = table_ref_data.get('datasetId')
            table_id = table_ref_data.get('tableId')
            if (isinstance(project_id, str) and project_id and
                isinstance(dataset_id, str) and dataset_id and
                isinstance(table_id, str) and table_id):
              table_ref_obj = BigQueryTable(project_id, dataset_id, table_id)
          chosen = item.get('chosen') is True
          saved_str = item.get('estimatedBytesSaved', '0')
          estimated_bytes_saved = (int(saved_str)
                                   if isinstance(saved_str, str) and
                                   saved_str.isdigit() else 0)
          rejected_reason = str(item.get('rejectedReason', ''))
          materialized_view.append({
              'chosen': chosen,
              'estimatedBytesSaved': estimated_bytes_saved,
              'rejectedReason': rejected_reason,
              'tableReference': table_ref_obj,
          })
    return {'materialView': materialized_view}

  @property
  def metadata_cache_statistics(self) -> dict[str, Any]:
    stats_list = self._query_stats.get('metadataCacheStatistics')
    metadata_cache = []
    if isinstance(stats_list, list):
      for item in stats_list:
        if isinstance(item, dict):
          table_ref_data = item.get('tableReference')
          table_ref_obj = None
          if isinstance(table_ref_data, dict):
            project_id = table_ref_data.get('projectId')
            dataset_id = table_ref_data.get('datasetId')
            table_id = table_ref_data.get('tableId')
            if (isinstance(project_id, str) and project_id and
                isinstance(dataset_id, str) and dataset_id and
                isinstance(table_id, str) and table_id):
              table_ref_obj = BigQueryTable(project_id, dataset_id, table_id)
          metadata_cache.append({
              'explanation': item.get('explanation', ''),
              'unusedReason': str(item.get('unusedReason', '')),
              'tableReference': table_ref_obj,
          })
    return {'tableMetadataCacheUsage': metadata_cache}

  # Properties derived from _information_schema_job_metadata
  @property
  def information_schema_user_email(self) -> str | None:
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    return self._information_schema_job_metadata.get('user_email')

  @property
  def information_schema_start_time_str(self) -> str | None:
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    return self._information_schema_job_metadata.get('start_time_str')

  @property
  def information_schema_end_time_str(self) -> str | None:
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    return self._information_schema_job_metadata.get('end_time_str')

  @property
  def information_schema_query(self) -> str | None:
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    return self._information_schema_job_metadata.get('query')

  @property
  def information_schema_total_modified_partitions(self) -> Union[int, str]:
    """The total number of partitions the job modified.

    This field is populated for LOAD and QUERY jobs.
    """
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    try:
      total_modified_partitions = self._information_schema_job_metadata[
          'total_modified_partitions']
      return total_modified_partitions
    except KeyError:
      return C_NOT_AVAILABLE

  @property
  def information_schema_resource_warning(self) -> str:
    """The warning message that appears if the resource usage during query

    processing is above the internal threshold of the system.
    """
    if not self._information_schema_job_metadata:
      return C_NOT_AVAILABLE
    try:
      resource_warning = self._information_schema_job_metadata['query_info'][
          'resource_warning']
      return resource_warning
    except KeyError:
      return C_NOT_AVAILABLE

  @property
  def information_schema_normalized_literals(self) -> str:
    """Contains the hashes of the query."""
    try:
      query_hashes = self._information_schema_job_metadata['query_info'][
          'query_hashes']['normalized_literals']
      return query_hashes
    except KeyError:
      return C_NOT_AVAILABLE


@caching.cached_api_call
def get_bigquery_job_api_resource_data(
    project_id: str,
    region: str,
    job_id: str,
) -> Union[dict[str, Any], None]:
  """Fetch a specific BigQuery job's raw API resource data."""
  api = apis.get_api('bigquery', 'v2', project_id)
  query_job = api.jobs().get(projectId=project_id,
                             location=region,
                             jobId=job_id)

  try:
    resp = query_job.execute(num_retries=config.API_RETRIES)
    return resp
  except errors.HttpError as err:
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_information_schema_job_metadata(
    context: models.Context,
    project_id: str,
    region: str,
    job_id: str,
    creation_time_milis: Optional[int] = None,
    skip_permission_check: bool = False,
) -> Optional[dict[str, Any]]:
  """Fetch metadata about a BigQuery job from the INFORMATION_SCHEMA."""
  if not apis.is_enabled(project_id, 'bigquery'):
    return None
  user_email = ''
  try:
    user_email = apis.get_user_email()
  except (RuntimeError, exceptions.DefaultCredentialsError):
    pass
  except AttributeError as err:
    if (('has no attribute' in str(err)) and
        ('with_quota_project' in str(err))):
      op.info('Running the investigation within the GCA context.')
  user = 'user:' + user_email
  if not skip_permission_check:
    try:
      policy = iam.get_project_policy(context)
      if (not policy.has_permission(user, 'bigquery.jobs.create')) or (
          not policy.has_permission(user, 'bigquery.jobs.listAll')):
        op.info(
            f'WARNING: Unable to run INFORMATION_SCHEMA view analysis due to missing permissions.\
            \nMake sure to grant {user_email} "bigquery.jobs.create" and "bigquery.jobs.listAll".\
            \nContinuing the investigation with the BigQuery job metadata obtained from the API.'
        )
        return None
    except utils.GcpApiError:
      op.info(
          'Attempting to query INFORMATION_SCHEMA with no knowledge of project'
          ' level permissions        \n(due to missing'
          ' resourcemanager.projects.get permission).')
  else:
    op.info(
        'Attempting to query INFORMATION_SCHEMA without checking project level permissions.'
    )
  try:
    creation_time_milis_filter = ' '
    if creation_time_milis:
      creation_time_milis_filter = (
          f'AND creation_time = TIMESTAMP_MILLIS({creation_time_milis})')
    query = f"""
    SELECT
        user_email, start_time, end_time, query
      FROM
        `{project_id}`.`region-{region}`.INFORMATION_SCHEMA.JOBS
      WHERE
        job_id = '{job_id}'
        {creation_time_milis_filter}
      LIMIT 1
    """
    results = get_query_results(
        project_id=project_id,
        query=query,
        location=region,
        timeout_sec=30,
        poll_interval_sec=2,  # Short poll interval
    )
    if not results or len(results) != 1:
      # We cannot raise an exception otherwise tests that use get_bigquery_job would fail
      # raise ValueError(f"Job {job_id} not found in INFORMATION_SCHEMA")
      return None
    return results[0]
  except errors.HttpError as err:
    logging.warning(
        'Failed to retrieve INFORMATION_SCHEMA job metadata for job %s: %s',
        job_id,
        err,
    )
    return None
  except KeyError as err:
    logging.warning(
        'Failed to parse INFORMATION_SCHEMA response for job %s: %s',
        job_id,
        err,
    )
    return None


def get_bigquery_job(
    context: models.Context,
    region: str,
    job_id: str,
    skip_permission_check: bool = False) -> Union[BigQueryJob, None]:
  """Fetch a BigQuery job, combining API and INFORMATION_SCHEMA data."""
  project_id = context.project_id
  if not project_id:
    return None
  try:
    job_api_resource_data = get_bigquery_job_api_resource_data(
        project_id, region, job_id)
    if not job_api_resource_data:
      return None
  except utils.GcpApiError as err:
    # This will be returned when permissions to fetch a job are missing.
    if 'permission' in err.message.lower():
      user_email = ''
      try:
        user_email = apis.get_user_email()
      except (RuntimeError, AttributeError,
              exceptions.DefaultCredentialsError) as error:
        if (('has no attribute' in str(error)) and
            ('with_quota_project' in str(error))):
          op.info('Running the investigation within the GCA context.')
      logging.debug(('Could not retrieve BigQuery job %s.\
          \n make sure to give the bigquery.jobs.get and bigquery.jobs.create permissions to %s',
                     (project_id + ':' + region + '.' + job_id), user_email))
      raise utils.GcpApiError(err)
    # This will be returned when a job is not found.
    elif 'not found' in err.message.lower():
      job_id_string = project_id + ':' + region + '.' + job_id
      logging.debug('Could not find BigQuery job %s', job_id_string)
      return None
    else:
      logging.debug((
          'Could not retrieve BigQuery job %s due to an issue calling the API. \
            Please restart the investigation.',
          (project_id + ':' + region + '.' + job_id)))
      return None
  information_schema_job_metadata = {}
  job_creation_millis = None
  creation_time_str = job_api_resource_data.get('statistics',
                                                {}).get('creationTime')
  if creation_time_str:
    try:
      job_creation_millis = int(creation_time_str)
    except (ValueError, TypeError):
      pass
  information_schema_job_metadata = get_information_schema_job_metadata(
      context, project_id, region, job_id, job_creation_millis,
      skip_permission_check)
  return BigQueryJob(
      project_id=project_id,
      job_api_resource_data=job_api_resource_data,
      information_schema_job_metadata=information_schema_job_metadata)


def _parse_value(field_schema: dict, value_data: Any) -> Any:
  """Recursively parses a BigQuery TableCell value."""
  if value_data is None:
    return None
  if field_schema.get('mode') == 'REPEATED':
    if not isinstance(value_data, list):
      # This can happen for an empty repeated field, which is represented as None
      return []
    # For repeated fields, the value is a list of {'v': ...} objects.
    # The schema for each item is the same field schema but with mode set to NULLABLE.
    item_schema = field_schema.copy()
    item_schema['mode'] = 'NULLABLE'
    return [_parse_value(item_schema, item.get('v')) for item in value_data]
  if field_schema.get('type') in ('RECORD', 'STRUCT'):
    # For record fields, the value is a dictionary {'f': [...]}.
    # The schema for the record's fields is in field_schema['fields'].
    if isinstance(value_data, dict) and 'f' in value_data:
      return _parse_row(field_schema.get('fields', []), value_data['f'])
    return {}
  # For scalar types, the value is directly in 'v'.
  # BigQuery API returns numbers as strings, so we leave them as is.
  # The consumer can perform type conversion if needed.
  return value_data


def _parse_row(schema_fields: List[dict],
               row_cells: List[dict]) -> dict[str, Any]:
  """Parses a BigQuery TableRow into a dictionary."""
  row_dict = {}
  for i, field_schema in enumerate(schema_fields):
    field_name = field_schema.get('name')
    if field_name and i < len(row_cells):
      cell_data = row_cells[i]
      row_dict[field_name] = _parse_value(field_schema, cell_data.get('v'))
  return row_dict


def get_query_results(
    project_id: str,
    query: str,
    location: Optional[str] = None,
    timeout_sec: int = 30,
    poll_interval_sec: int = 2,
) -> Optional[List[dict[str, Any]]]:
  """Executes a BigQuery query, waits for completion, and returns the results.

  Args:
      project_id: The GCP project ID where the query should run.
      query: The SQL query string to execute.
      location: The location (e.g., 'US', 'EU', 'us-central1') where the job
        should run. If None, BigQuery defaults might apply, often based on
        dataset locations if referenced.
      timeout_sec: Maximum time in seconds to wait for the query job to
        complete.
      poll_interval_sec: Time in seconds between polling the job status.

  Returns:
      A list of dictionaries representing the result rows, or None if the
      query fails, times out, or the API is disabled.
  Raises:
      utils.GcpApiError: If an unrecoverable API error occurs during job
                         insertion, status check, or result fetching.
  """
  if not apis.is_enabled(project_id, 'bigquery'):
    logging.warning('BigQuery API is not enabled in project %s.', project_id)
    return None
  api = apis.get_api('bigquery', 'v2', project_id)
  job_id = f'gcpdiag_query_{uuid.uuid4()}'
  job_body = {
      'jobReference': {
          'projectId': project_id,
          'jobId': job_id,
          'location': location,  # Location can be None
      },
      'configuration': {
          'query': {
              'query': query,
              'useLegacySql': False,
              # Consider adding priority, destinationTable, etc. if needed
          }
      },
  }
  try:
    logging.debug(
        'Starting BigQuery job %s in project %s, location %s',
        job_id,
        project_id,
        location or 'default',
    )
    insert_request = api.jobs().insert(projectId=project_id, body=job_body)
    insert_response = insert_request.execute(num_retries=config.API_RETRIES)
    job_ref = insert_response['jobReference']
    actual_job_id = job_ref['jobId']
    actual_location = job_ref.get('location')  # Get location assigned by BQ
    logging.debug('Job %s created. Polling for completion...', actual_job_id)
    start_time = time.time()
    while True:
      # Check for timeout
      if time.time() - start_time > timeout_sec:
        logging.error(
            'BigQuery job %s timed out after %d seconds.',
            actual_job_id,
            timeout_sec,
        )
        return None
      # Get job status
      logging.debug('>>> Getting job status for %s', actual_job_id)
      get_request = api.jobs().get(
          projectId=job_ref['projectId'],
          jobId=actual_job_id,
          location=actual_location,
      )
      job_status_response = get_request.execute(num_retries=config.API_RETRIES)
      status = job_status_response.get('status', {})
      logging.debug('>>> Job status: %s', status.get('state'))
      if status.get('state') == 'DONE':
        if status.get('errorResult'):
          error_info = status['errorResult']
          if 'User does not have permission to query table' in error_info.get(
              'message'):
            op.info(
                error_info.get('message')[15:] +
                '\nContinuing the investigation with the job metadata obtained from the API.'
            )
          else:
            error_info = status['errorResult']
            logging.error(
                'BigQuery job %s failed. Reason: %s, Message: %s',
                actual_job_id,
                error_info.get('reason'),
                error_info.get('message'),
            )
            # Log detailed errors if available
            for error in status.get('errors', []):
              logging.error(
                  '  - Detail: %s (Location: %s)',
                  error.get('message'),
                  error.get('location'),
              )
          return None
        else:
          logging.debug('BigQuery job %s completed successfully.',
                        actual_job_id)
          break  # Job finished successfully
      elif status.get('state') in ['PENDING', 'RUNNING']:
        logging.debug('>>> Job running, sleeping...')
        # Job still running, wait and poll again
        time.sleep(poll_interval_sec)
      else:
        # Unexpected state
        logging.error(
            'BigQuery job %s entered unexpected state: %s',
            actual_job_id,
            status.get('state', 'UNKNOWN'),
        )
        return None
    # Fetch results
    logging.debug('>>> Fetching results for job %s...',
                  actual_job_id)  # <-- ADD
    results_request = api.jobs().getQueryResults(
        projectId=job_ref['projectId'],
        jobId=actual_job_id,
        location=actual_location,
        # Add startIndex, maxResults for pagination if needed
    )
    results_response = results_request.execute(num_retries=config.API_RETRIES)
    # Check if job actually completed (getQueryResults might return before DONE sometimes)
    if not results_response.get('jobComplete', False):
      logging.warning(
          'getQueryResults returned jobComplete=False for job %s, results might'
          ' be incomplete.',
          actual_job_id,
      )
      # Decide if you want to wait longer or return potentially partial results
    rows = []
    if 'rows' in results_response and 'schema' in results_response:
      schema_fields = results_response['schema'].get('fields')
      if not schema_fields:
        return []
      for row_data in results_response['rows']:
        if 'f' in row_data:
          rows.append(_parse_row(schema_fields, row_data['f']))
    if results_response.get('pageToken'):
      logging.warning(
          'Query results for job %s are paginated, but pagination '
          'is not yet implemented.',
          actual_job_id,
      )
    return rows
  except errors.HttpError as err:
    logging.error('API error during BigQuery query execution for job %s: %s',
                  job_id, err)
    # Raise specific GcpApiError if needed for upstream handling
    raise utils.GcpApiError(err) from err
  except Exception as e:
    logging.exception(
        'Unexpected error during BigQuery query execution for job %s: %s',
        job_id,
        e,
    )
    # Re-raise or handle as appropriate
    raise


@caching.cached_api_call
def get_bigquery_project(project_id: str) -> crm.Project:
  """Attempts to retrieve project details for the supplied BigQuery project id or number.

    If the project is found/accessible, it returns a Project object with the resource data.
    If the project cannot be retrieved, the application raises one of the exceptions below.
    The get_bigquery_project method avoids unnecessary printing of the error message to keep
    the user interface of the tool cleaner to focus on meaningful investigation results.
    Corresponding errors are handled gracefully downstream.

    Args:
        project_id (str): The project id or number of
        the project (e.g., "123456789", "example-project").

    Returns:
        Project: An object representing the BigQuery project's full details.

    Raises:
        utils.GcpApiError: If there is an issue calling the GCP/HTTP Error API.

    Usage:
        When using project identifier from gcpdiag.models.Context

        project = crm.get_project(context.project_id)

        An unknown project identifier
        try:
          project = crm.get_project("123456789")
        except:
          # Handle exception
        else:
          # use project data
  """
  try:
    logging.debug('retrieving project %s ', project_id)
    crm_api = apis.get_api('cloudresourcemanager', 'v3', project_id)
    request = crm_api.projects().get(name=f'projects/{project_id}')
    response = request.execute(num_retries=config.API_RETRIES)
  except errors.HttpError as e:
    error = utils.GcpApiError(response=e)
    raise error from e
  else:
    return crm.Project(resource_data=response)


@caching.cached_api_call
def get_table(project_id: str, dataset_id: str,
              table_id: str) -> Optional[Dict[str, Any]]:
  """Retrieves a BigQuery table resource if it exists.

  Args:
    project_id: The project ID.
    dataset_id: The dataset ID.
    table_id: The table ID.

  Returns:
    A dictionary representing the table resource, or None if not found.
  """
  try:
    api = apis.get_api('bigquery', 'v2', project_id)
    request = api.tables().get(projectId=project_id,
                               datasetId=dataset_id,
                               tableId=table_id)
    response = request.execute(num_retries=config.API_RETRIES)
    return response
  except errors.HttpError as err:
    if err.resp.status == 404:
      return None
    raise utils.GcpApiError(err) from err
