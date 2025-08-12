# Copyright 2025 Google LLC
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
"""Queries related to GCP Looker Core."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, MutableMapping

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, apis_utils


class Instance(models.Resource):
  """Represents a Looker Core Instance."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    return '/'.join(self.full_path.split('/')[-4:])

  @property
  def status(self) -> str:
    return self._resource_data.get('state', 'STATE_UNSPECIFIED')

  @property
  def create_time(self) -> str:
    return self._resource_data.get('createTime', '')

  @property
  def update_time(self) -> str:
    return self._resource_data.get('updateTime', '')

  @property
  def platform_edition(self) -> str:
    return self._resource_data.get('platformEdition', '')

  @property
  def looker_version(self) -> str:
    return self._resource_data.get('lookerVersion', '')

  @property
  def looker_uri(self) -> str:
    return self._resource_data.get('lookerUri', '')


class Operation(models.Resource):
  """Represents Looker Core long-running operation."""

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    return self._resource_data.get('name', '')

  @property
  def name(self) -> str:
    return self._resource_data['name'].split('/')[-1]

  @property
  def metadata(self) -> dict:
    return self._resource_data.get('metadata', {})

  @property
  def done(self) -> bool:
    return self._resource_data.get('done', False)

  @property
  def target(self) -> str:
    return self._resource_data.get('metadata', {}).get('target', '')

  @property
  def verb(self) -> str:
    return self._resource_data.get('metadata', {}).get('verb', '')

  @property
  def status(self) -> str:
    return 'Completed' if self._resource_data.get('done') else 'In Progress'

  @property
  def location_id(self) -> str:
    parts = self._resource_data.get('name', '').split('/')
    return parts[3] if len(parts) > 3 else ''

  @property
  def instance_name(self) -> str:
    parts = self.target.split('/')
    return parts[5] if len(parts) >= 6 else ''

  @property
  def operation_type(self) -> str:
    return self.verb

  @property
  def action(self) -> str:
    if self.verb == 'update' and not self.done:
      return 'Updating Instance'
    else:
      parts = self.target.split('/')
      return parts[6] if len(parts) >= 7 else ''

  @property
  def create_time(self) -> datetime:
    create_time_str = self._resource_data.get('metadata',
                                              {}).get('createTime', '')
    if create_time_str:
      return datetime.fromisoformat(
          create_time_str.rstrip('Z')).replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def _get_locations_to_scan(context: models.Context, looker_api) -> List[str]:
  """Returns a list of locations to scan based on the context."""
  if context.locations_pattern:
    return str(context.locations_pattern.pattern).split('|')
  try:
    request = looker_api.projects().locations().list(
        name=f'projects/{context.project_id}')
    return [
        loc['locationId'] for loc in apis_utils.list_all(
            request=request,
            next_function=looker_api.projects().locations().list_next,
            response_keyword='locations')
    ]
  except googleapiclient.errors.HttpError as err:
    logging.error('Error fetching locations: %s', err)
    raise utils.GcpApiError(err) from err


@caching.cached_api_call
def get_instances(context: models.Context) -> Dict[str, Instance]:
  """Get a list of Instances from the given GCP project."""
  instances: Dict[str, Instance] = {}
  if not apis.is_enabled(context.project_id, 'looker'):
    return instances
  looker_api = apis.get_api('looker', 'v1', context.project_id)

  try:
    locations_to_scan = _get_locations_to_scan(context, looker_api)
  except utils.GcpApiError as err:
    raise err

  for loc_id in locations_to_scan:
    try:
      parent_path = f'projects/{context.project_id}/locations/{loc_id}'
      request = looker_api.projects().locations().instances().list(
          parent=parent_path)
      for inst in apis_utils.list_all(
          request=request,
          next_function=looker_api.projects().locations().instances().list_next,
          response_keyword='instances'):
        if not context.match_project_resource(resource=inst.get('name', '')):
          continue
        instance = Instance(project_id=context.project_id, resource_data=inst)
        instances[instance.name] = instance
    except googleapiclient.errors.HttpError as err:
      logging.warning('Could not list instances for location %s: %s', loc_id,
                      err)
      continue
  return instances


@caching.cached_api_call
def get_operations(
    context: models.Context
) -> MutableMapping[str, MutableMapping[str, List[Operation]]]:
  """Get a list of recent operations from the given GCP project."""
  location_instance_operations: MutableMapping[str, MutableMapping[
      str, List[Operation]]] = {}
  if not apis.is_enabled(context.project_id, 'looker'):
    return location_instance_operations

  looker_api = apis.get_api('looker', 'v1', context.project_id)

  now = context.parameters.get('now', datetime.now(timezone.utc))
  one_day_ago = now - timedelta(days=1)

  try:
    locations_to_scan = _get_locations_to_scan(context, looker_api)
  except utils.GcpApiError:
    return {}

  for location_id in locations_to_scan:
    try:
      op_request_name = f'projects/{context.project_id}/locations/{location_id}'
      operations_request = looker_api.projects().locations().operations().list(
          name=op_request_name)
      for resp_op in apis_utils.list_all(request=operations_request,
                                         next_function=looker_api.projects().
                                         locations().operations().list_next,
                                         response_keyword='operations'):
        operation_details = looker_api.projects().locations().operations().get(
            name=resp_op['name']).execute(num_retries=config.API_RETRIES)
        operation = Operation(project_id=context.project_id,
                              resource_data=operation_details)

        if operation.create_time >= one_day_ago:
          location_instance_operations.setdefault(operation.location_id,
                                                  {}).setdefault(
                                                      operation.instance_name,
                                                      []).append(operation)
    except googleapiclient.errors.HttpError as err:
      logging.warning('Could not list operations for location %s: %s',
                      location_id, err)
      continue

  return location_instance_operations
