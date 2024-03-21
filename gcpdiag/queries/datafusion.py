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
"""Queries related to Data Fusion."""

import datetime
import ipaddress
import logging
import re
from typing import Dict, Iterable, List, Mapping, Optional

import googleapiclient.errors
import requests
from bs4 import BeautifulSoup

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, crm, network
from gcpdiag.utils import Version

# To avoid name conflict with L145
IPv4NetOrIPv6Net = network.IPv4NetOrIPv6Net


class Instance(models.Resource):
  """Represents a Data Fusion instance.

  https://cloud.google.com/data-fusion/docs/reference/rest/v1/projects.locations.instances#Instance
  """

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """
    The 'name' of the instance is already in the full path form

    projects/{project}/locations/{location}/instances/{instance}.
    """
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/instances/', '/', path)
    return path

  @property
  def name(self) -> str:
    return utils.extract_value_from_res_name(self._resource_data['name'],
                                             'instances')

  @property
  def location(self) -> str:
    return utils.extract_value_from_res_name(self._resource_data['name'],
                                             'locations')

  @property
  def zone(self) -> str:
    return self._resource_data['zone']

  @property
  def type(self) -> str:
    return self._resource_data['type']

  @property
  def is_basic_type(self) -> bool:
    return self._resource_data['type'] == 'BASIC'

  @property
  def is_enterprise_type(self) -> bool:
    return self._resource_data['type'] == 'ENTERPRISE'

  @property
  def is_developer_type(self) -> bool:
    return self._resource_data['type'] == 'DEVELOPER'

  @property
  def is_private(self) -> bool:
    if 'privateInstance' in self._resource_data:
      return self._resource_data['privateInstance']
    return False

  @property
  def status(self) -> str:
    return self._resource_data['state']

  @property
  def is_running(self) -> bool:
    return self.status == 'ACTIVE'

  @property
  def is_deleting(self) -> bool:
    return self._resource_data['state'] == 'DELETING'

  @property
  def version(self) -> Version:
    return Version(self._resource_data['version'])

  @property
  def api_service_agent(self) -> str:
    return self._resource_data['p4ServiceAccount']

  @property
  def dataproc_service_account(self) -> str:
    sa = self._resource_data.get('dataprocServiceAccount')
    if sa is None:
      sa = crm.get_project(self.project_id).default_compute_service_account
    return sa

  @property
  def tenant_project_id(self) -> str:
    return self._resource_data['tenantProjectId']

  @property
  def uses_shared_vpc(self) -> bool:
    """
    If shared VPC then 'network_string' = 'projects/{host-project-id}/global/networks/{network}'
    else 'network_string' = {network}
    """
    if 'network' in self._resource_data['networkConfig']:
      network_string = self._resource_data['networkConfig']['network']
      match = re.match(r'projects/([^/]+)/global/networks/([^/]+)$',
                       network_string)
      if match and match.group(1) != self.project_id:
        return True

    return False

  @property
  def network(self) -> network.Network:
    if 'network' in self._resource_data['networkConfig']:
      network_string = self._resource_data['networkConfig']['network']
      match = re.match(r'projects/([^/]+)/global/networks/([^/]+)$',
                       network_string)
      if match:
        return network.get_network(match.group(1), match.group(2))
      else:
        return network.get_network(self.project_id, network_string)

    return network.get_network(self.project_id, 'default')

  @property
  def tp_ipv4_cidr(self) -> Optional[IPv4NetOrIPv6Net]:
    if 'network' in self._resource_data['networkConfig']:
      cidr = self._resource_data['networkConfig']['ipAllocation']
      return ipaddress.ip_network(cidr)
    return None

  @property
  def api_endpoint(self) -> str:
    return self._resource_data['apiEndpoint']


@caching.cached_api_call
def get_instances(context: models.Context) -> Mapping[str, Instance]:
  """Get a dict of Instance matching the given context, indexed by instance full path."""
  instances: Dict[str, Instance] = {}

  if not apis.is_enabled(context.project_id, 'datafusion'):
    return instances

  logging.info('fetching list of Data Fusion instances in project %s',
               context.project_id)
  datafusion_api = apis.get_api('datafusion', 'v1', context.project_id)
  query = datafusion_api.projects().locations().instances().list(
      parent=f'projects/{context.project_id}/locations/-'
  )  #'-' (wildcard) all regions

  try:
    resp = query.execute(num_retries=config.API_RETRIES)
    if 'instances' not in resp:
      return instances

    for i in resp['instances']:
      # projects/{project}/locations/{location}/instances/{instance}.
      result = re.match(r'projects/[^/]+/locations/([^/]+)/instances/([^/]+)',
                        i['name'])
      if not result:
        logging.error('invalid datafusion name: %s', i['name'])
        continue
      location = result.group(1)
      labels = i.get('labels', {})
      name = result.group(2)
      if not context.match_project_resource(
          location=location, labels=labels, resource=name):
        continue

      instances[i['name']] = Instance(project_id=context.project_id,
                                      resource_data=i)

  except googleapiclient.errors.HttpError as err:
    raise utils.GcpApiError(err) from err

  return instances


@caching.cached_api_call
def extract_support_datafusion_version() -> Dict[str, str]:
  """Extract the version policy dictionary from the data fusion version support policy page.

  Returns:
    A dictionary of data fusion versions and their support end dates.
  """
  page_url = 'https://cloud.google.com/data-fusion/docs/support/version-support-policy'

  try:
    response = requests.get(page_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    data_fusion_table = soup.find('table')
    if data_fusion_table:
      versions = []
      support_end_dates = []
      version_policy_dict = {}

      for row in data_fusion_table.find_all('tr')[1:]:
        columns = row.find_all('td')
        version = columns[0]
        support_end_date = columns[2].text.strip()
        if version.sup:
          version.sup.decompose()

        version = version.text.strip()
        try:
          support_end_date = datetime.datetime.strptime(support_end_date,
                                                        '%B %d, %Y')
          support_end_date = datetime.datetime.strftime(support_end_date,
                                                        '%Y-%m-%d')
        except ValueError:
          continue

        versions.append(version)
        support_end_dates.append(support_end_date)

        version_policy_dict = dict(zip(versions, support_end_dates))
      return version_policy_dict

    else:
      return {}

  except (
      requests.exceptions.RequestException,
      AttributeError,
      TypeError,
      ValueError,
      IndexError,
  ) as e:
    logging.error('Error in extracting data fusion version support policy: %s',
                  e)
    return {}


class Profile(models.Resource):
  """Represents a Compute Profile."""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  @property
  def short_path(self) -> str:
    path = self.full_path
    return path

  @property
  def name(self) -> str:
    return self._resource_data['name']

  @property
  def region(self) -> str:
    for value in self._resource_data['provisioner'].get('properties'):
      if value.get('name') == 'region' and value.get('value') is not None:
        return value.get('value')
    return 'No region defined'

  @property
  def status(self) -> str:
    return self._resource_data['status']

  @property
  def scope(self) -> str:
    return self._resource_data['scope']

  @property
  def is_dataproc_provisioner(self) -> bool:
    return self._resource_data['provisioner']['name'] == 'gcp-dataproc'

  @property
  def is_existing_dataproc_provisioner(self) -> bool:
    return self._resource_data['provisioner']['name'] == 'gcp-existing-dataproc'

  @property
  def autoscaling_enabled(self) -> bool:
    for value in self._resource_data['provisioner'].get('properties'):
      if (value.get('name') == 'enablePredefinedAutoScaling' and
          value.get('value') is not None):
        return value.get('value') == 'true'
    return False

  @property
  def image_version(self) -> str:
    for value in self._resource_data['provisioner'].get('properties'):
      if value.get('name') == 'imageVersion' and value.get('value') != '':
        return value.get('value')
    return 'No imageVersion defined'


@caching.cached_api_call
def get_instance_system_compute_profile(
    context: models.Context, instance: Instance) -> Iterable[Profile]:
  """Get a list of datafusion Instance dataproc System compute profile."""
  logging.info('fetching dataproc System compute profile list: %s',
               context.project_id)
  system_profiles: List[Profile] = []
  cdap_endpoint = instance.api_endpoint
  response = apis.make_request('GET', f'{cdap_endpoint}/v3/profiles')
  if response is not None:
    for res in response:
      if (res['provisioner']['name'] == 'gcp-dataproc' or
          res['provisioner']['name'] == 'gcp-existing-dataproc'):
        system_profiles.append(Profile(context.project_id, res))
  return system_profiles


@caching.cached_api_call
def get_instance_user_compute_profile(context: models.Context,
                                      instance: Instance) -> Iterable[Profile]:
  """Get a list of datafusion Instance dataproc User compute profile."""
  logging.info('fetching dataproc User compute profile list: %s',
               context.project_id)
  user_profiles: List[Profile] = []
  cdap_endpoint = instance.api_endpoint
  response_namespaces = apis.make_request('GET',
                                          f'{cdap_endpoint}/v3/namespaces')
  if response_namespaces is not None:
    for res in response_namespaces:
      response = apis.make_request(
          'GET', f"{cdap_endpoint}/v3/namespaces/{res['name']}/profiles")
      if response is not None:
        for res in response:
          if (res['provisioner']['name'] == 'gcp-dataproc' or
              res['provisioner']['name'] == 'gcp-existing-dataproc'):
            user_profiles.append(Profile(context.project_id, res))
      user_profiles = list(filter(bool, user_profiles))
  return user_profiles
