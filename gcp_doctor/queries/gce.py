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
"""Queries related to GCP Kubernetes Engine clusters."""

import logging
import re
from typing import Callable, Dict, Iterable, Mapping, Optional, Set

import googleapiclient.errors

from gcp_doctor import caching, config, models, utils
from gcp_doctor.queries import apis, crm


class ManagedInstanceGroup(models.Resource):
  """Represents a GCE managed instance group."""
  _resource_data: dict
  _region: Optional[str]

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._region = None

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    path = self.project_id + '/' + self.name
    return path

  def is_gke(self) -> bool:
    """Is this managed instance group part of a GKE cluster?

    Note that the results are based on heuristics (the mig name),
    which is not ideal.
    """

    # gke- is normal GKE, gk3- is GKE autopilot
    return self.name.startswith('gke-') or self.name.startswith('gk3-')

  @property
  def self_link(self) -> str:
    return self._resource_data['selfLink']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def region(self) -> str:
    if self._region is None:
      if 'region' in self._resource_data:
        m = re.search(r'/regions/([^/]+)$', self._resource_data['region'])
        if not m:
          raise RuntimeError('can\'t determine region of mig %s (%s)' %
                             (self.name, self._resource_data['region']))
        self._region = m.group(1)
      elif 'zone' in self._resource_data:
        m = re.search(r'/zones/([^/]+)$', self._resource_data['zone'])
        if not m:
          raise RuntimeError('can\'t determine region of mig %s (%s)' %
                             (self.name, self._resource_data['region']))
        zone = m.group(1)
        self._region = utils.zone_region(zone)
      else:
        raise RuntimeError(
            'can\'t determine region of mig %s, both region and zone aren\'t set!'
        )
    return self._region

  def is_instance_member(self, project_id: str, region: str,
                         instance_name: str):
    """Given the project_id, region and instance name, is it a member of this MIG?"""
    return self.project_id == project_id and self.region == region and \
        instance_name.startswith(self._resource_data['baseInstanceName'])


class Instance(models.Resource):
  """Represents a GCE instance."""
  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data
    self._metadata_dict = None

  @property
  def id(self) -> str:
    return self._resource_data['id']

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def full_path(self) -> str:
    result = re.match(r'https://www.googleapis.com/compute/v1/(.*)',
                      self._resource_data['selfLink'])
    if result:
      return result.group(1)
    else:
      return '>> ' + self._resource_data['selfLink']

  @property
  def short_path(self) -> str:
    # Note: instance names must be unique per project, so no need to add the zone.
    path = self.project_id + '/' + self.name
    return path

  def is_serial_port_logging_enabled(self) -> bool:
    value = self.get_metadata('serial-port-logging-enable')
    return bool(value and value.upper() == 'TRUE')

  def is_gke_node(self) -> bool:
    return 'labels' in self._resource_data and \
           'goog-gke-node' in self._resource_data['labels']

  @property
  def service_account(self) -> Optional[str]:
    if 'serviceAccounts' in self._resource_data:
      saccts = self._resource_data['serviceAccounts']
      if isinstance(saccts, list) and len(saccts) >= 1:
        return saccts[0]['email']
    return None

  def get_metadata(self, key: str) -> str:
    if not self._metadata_dict:
      self._metadata_dict = dict()
      if 'metadata' in self._resource_data and 'items' in self._resource_data[
          'metadata']:
        for item in self._resource_data['metadata']['items']:
          if 'key' in item and 'value' in item:
            self._metadata_dict[item['key']] = item['value']
    project_metadata = get_project_metadata(self.project_id)
    return self._metadata_dict.get(key, project_metadata.get(key))

  @property  # type: ignore
  @caching.cached_api_call(in_memory=True)
  def mig(self) -> ManagedInstanceGroup:
    """Return ManagedInstanceGroup that owns this instance.

    Throws AttributeError in case it isn't MIG-managed."""

    created_by = self.get_metadata('created-by')
    if created_by is None:
      raise AttributeError(f'instance {self.id} is not managed by a mig')

    # Example created-by:
    # pylint: disable=line-too-long
    # "projects/18404348413/zones/europe-west4-a/instanceGroupManagers/gke-gke1-default-pool-e5e20a34-grp"
    # (note how it uses a project number and not a project id...)
    created_by_match = re.match(
        r'projects/([^/]+)/((?:regions|zones)/[^/]+/instanceGroupManagers/[^/]+)$',
        created_by)
    if not created_by_match:
      raise AttributeError(
          f'instance {self.id} is not managed by a mig (created-by={created_by})'
      )
    project = crm.get_project(created_by_match.group(1))

    mig_self_link = ('https://www.googleapis.com/compute/v1/'
                     f'projects/{project.id}/{created_by_match.group(2)}')

    # Try to find a matching mig.
    for mig in get_managed_instance_groups(
        models.Context(projects=[self.project_id])).values():
      if mig.self_link == mig_self_link:
        return mig

    raise AttributeError(f'instance {self.id} is not managed by a mig')


@caching.cached_api_call(in_memory=True)
def get_gce_zones(project_id: str) -> Set[str]:
  try:
    gce_api = apis.get_api('compute', 'v1', project_id)
    logging.info('listing gce zones of project %s', project_id)
    request = gce_api.zones().list(project=project_id)
    response = request.execute(num_retries=config.API_RETRIES)
    if not response or 'items' not in response:
      return set()
    return {item['name'] for item in response['items'] if 'name' in item}
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err


def batch_fetch_all(api, requests: Iterable, next_function: Callable,
                    log_text: str):
  try:
    items = []
    additional_pages_to_fetch = []
    pending_requests = list(requests)

    def fetch_all_cb(request_id, response, exception):
      if exception:
        logging.error('exception when %s: %s', log_text, exception)
        return
      if not response or 'items' not in response:
        return
      items.extend(response['items'])
      if 'nextPageToken' in response and response['nextPageToken']:
        additional_pages_to_fetch.append(
            (pending_requests[int(request_id)], response))

    page = 1
    while pending_requests:
      batch = api.new_batch_http_request()
      for i, req in enumerate(pending_requests):
        batch.add(req, callback=fetch_all_cb, request_id=str(i))
      if page <= 1:
        logging.info(log_text)
      else:
        logging.info('%s (page: %d)', log_text, page)
      batch.execute()

      # Do we need to fetch any additional pages?
      pending_requests = []
      for p in additional_pages_to_fetch:
        req = next_function(p[0], p[1])
        if req:
          pending_requests.append(req)
      additional_pages_to_fetch = []
      page += 1
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  return items


@caching.cached_api_call(in_memory=True)
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  """Get a list of Instance matching the given context, indexed by instance id."""

  instances: Dict[str, Instance] = {}
  for project_id in context.projects:
    gce_api = apis.get_api('compute', 'v1', project_id)
    requests = [
        gce_api.instances().list(project=project_id, zone=zone)
        for zone in get_gce_zones(project_id)
    ]
    items = batch_fetch_all(
        api=gce_api,
        requests=requests,
        next_function=gce_api.instances().list_next,
        log_text=f'listing gce instances of project {project_id}')
    for i in items:
      result = re.match(
          r'https://www.googleapis.com/compute/v1/projects/([^/]+)/zones/([^/]+)/',
          i['selfLink'])
      if not result:
        logging.error('instance %s selfLink didn\'t match regexp: %s', i['id'],
                      i['selfLink'])
        continue
      project_id = result.group(1)
      zone = result.group(2)
      labels = i.get('labels', {})
      if not context.match_project_resource(location=zone, labels=labels):
        continue
      instances[i['id']] = Instance(project_id=project_id, resource_data=i)
  return instances


@caching.cached_api_call(in_memory=True)
def get_managed_instance_groups(
    context: models.Context) -> Mapping[int, ManagedInstanceGroup]:
  """Get a list of ManagedInstanceGroups matching the given context, indexed by mig id."""

  migs: Dict[int, ManagedInstanceGroup] = {}
  for project_id in context.projects:
    gce_api = apis.get_api('compute', 'v1', project_id)
    requests = [
        gce_api.instanceGroupManagers().list(project=project_id, zone=zone)
        for zone in get_gce_zones(project_id)
    ]
    items = batch_fetch_all(
        api=gce_api,
        requests=requests,
        next_function=gce_api.instances().list_next,
        log_text=f'listing managed instance groups of project {project_id}')
    for i in items:
      result = re.match(
          r'https://www.googleapis.com/compute/v1/projects/([^/]+)/(?:regions|zones)/([^/]+)/',
          i['selfLink'])
      if not result:
        logging.error('mig %s selfLink didn\'t match regexp: %s', i['name'],
                      i['selfLink'])
        continue
      project_id = result.group(1)
      location = result.group(2)
      labels = i.get('labels', {})
      if not context.match_project_resource(location=location, labels=labels):
        continue
      migs[i['id']] = ManagedInstanceGroup(project_id=project_id,
                                           resource_data=i)
  return migs


@caching.cached_api_call
def get_project_metadata(project_id) -> Mapping[str, str]:
  gce_api = apis.get_api('compute', 'v1', project_id)
  logging.info('fetching metadata of project %s', project_id)
  query = gce_api.projects().get(project=project_id)
  try:
    response = query.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  mapped_metadata: Dict[str, str] = {}
  metadata = response.get('commonInstanceMetadata')
  if metadata and 'items' in metadata:
    for m_item in metadata['items']:
      mapped_metadata[m_item.get('key')] = m_item.get('value')
  return mapped_metadata
