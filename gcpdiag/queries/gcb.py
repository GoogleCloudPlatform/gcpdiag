# Copyright 2021 Google LLC
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

# Lint as: python3
"""Queries related to GCP Cloud Build instances."""

import dataclasses
import logging
from typing import Dict, List, Mapping, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


@dataclasses.dataclass(frozen=True)
class BuildOptions:
  """representation of build.options object"""
  logging: str
  log_streaming_option: str

  def is_bucket_streaming_enabled(self) -> bool:
    return (self.logging != 'GCS_ONLY' or
            self.log_streaming_option != 'STREAM_OFF')


class BuildOptionsBuilder:
  """Build options builder from dictionary."""

  def __init__(self, options: dict):
    self._options = options

  def build(self) -> BuildOptions:
    return BuildOptions(
        logging=self._get_logging(),
        log_streaming_option=self._get_log_streaming_option(),
    )

  def _get_logging(self) -> str:
    return self._options.get('logging', 'LEGACY')

  def _get_log_streaming_option(self) -> str:
    return self._options.get('logStreamingOption', 'LOGGING_UNSPECIFIED')


@dataclasses.dataclass(frozen=True)
class FailureInfo:
  """Wrapper around build.failureInfo object."""
  failure_type: str


class FailureInfoBuilder:
  """Wrapper around build.failureInfo object."""

  def __init__(self, failure_info: dict):
    self._failure_info = failure_info

  def build(self) -> FailureInfo:
    return FailureInfo(failure_type=self._get_failure_type())

  def _get_failure_type(self) -> str:
    return self._failure_info.get('type', '')


class Build(models.Resource):
  """Represents a Cloud Build execution."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    return f'projects/{self.project_id}/locations/-/builds/{self.id}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.id
    return path

  @property
  def status(self) -> str:
    return self._resource_data['status']

  @property
  def service_account(self) -> Optional[str]:
    return self._resource_data.get('serviceAccount')

  @property
  def images(self) -> List[str]:
    return self._resource_data.get('images', [])

  @property
  def logs_bucket(self) -> str:
    return self._resource_data.get('logsBucket', '')

  @property
  def options(self) -> BuildOptions:
    return BuildOptionsBuilder(self._resource_data.get('options', {})).build()

  @property
  def failure_info(self) -> FailureInfo:
    return FailureInfoBuilder(self._resource_data.get('failureInfo',
                                                      {})).build()


class Trigger(models.Resource):
  """Represents a Cloud Build trigger instance."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def name(self) -> str:
    if 'name' not in self._resource_data:
      return ''
    return self._resource_data['name']

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def full_path(self) -> str:
    return f'projects/{self.project_id}/locations/-/triggers/{self.id}'

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.id
    return path


@caching.cached_api_call
def get_builds(context: models.Context) -> Mapping[str, Build]:
  """Get a list of Cloud Build instances matching the given context, indexed by Cloud Build id."""
  builds: Dict[str, Build] = {}
  if not apis.is_enabled(context.project_id, 'cloudbuild'):
    return builds
  build_api = apis.get_api('cloudbuild', 'v1', context.project_id)
  logging.info('fetching list of builds in the project %s', context.project_id)
  query = build_api.projects().locations().builds().list(
      parent=f'projects/{context.project_id}/locations/-')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'builds' not in resp:
      return builds
    for resp_f in resp['builds']:
      # verify that we have some minimal data that we expect
      if 'id' not in resp_f:
        raise RuntimeError(
            'missing data in projects.locations.builds.list response')
      f = Build(project_id=context.project_id, resource_data=resp_f)
      builds[f.id] = f
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return builds


@caching.cached_api_call
def get_triggers(context: models.Context) -> Mapping[str, Trigger]:
  """Get a list of Cloud Build triggers matching the given context,
     indexed by Cloud Build trigger id."""
  triggers: Dict[str, Trigger] = {}
  if not apis.is_enabled(context.project_id, 'cloudbuild'):
    return triggers
  build_api = apis.get_api('cloudbuild', 'v1', context.project_id)
  logging.info('fetching list of triggers in the project %s',
               context.project_id)
  query = build_api.projects().locations().triggers().list(
      parent=f'projects/{context.project_id}/locations/global')
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'triggers' not in resp:
      return triggers
    for resp_f in resp['triggers']:
      # verify that we have some minimal data that we expect
      if 'id' not in resp_f:
        raise RuntimeError(
            'missing data in projects.locations.triggers.list response')
      f = Trigger(project_id=context.project_id, resource_data=resp_f)
      triggers[f.id] = f
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err
  return triggers
