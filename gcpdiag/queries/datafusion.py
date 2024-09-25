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

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis, crm, html, network
from gcpdiag.queries.generic_api.api_build import get_generic
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
  def status_details(self) -> Optional[str]:
    if 'stateMessage' in self._resource_data:
      return self._resource_data['stateMessage']
    return None

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
    data_fusion_table = html.fetch_and_extract_table(page_url,
                                                     tag='h2',
                                                     tag_id='support_timelines')
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

  def __init__(self, project_id, instance_name, resource_data):
    super().__init__(project_id=project_id)
    self.instance_name = instance_name
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """The full path form :

    projects/{project}/instances/{instance}/computeProfiles/{profile}.
    """
    return (f'projects/{self.project_id}/instances/{self.instance_name}'
            f'/computeProfiles/{self._resource_data["name"]}')

  @property
  def short_path(self) -> str:
    """The short path form :

    {project}/{instance}/{profile}.
    """
    return (
        f'{self.project_id}/{self.instance_name}/{self._resource_data["name"]}')

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

  @property
  def auto_scaling_policy(self) -> str:
    for value in self._resource_data['provisioner'].get('properties'):
      if value.get('name') == 'autoScalingPolicy' and value.get('value') != '':
        return value.get('value')
    return 'No autoScalingPolicy defined'


@caching.cached_api_call
def get_instance_system_compute_profile(
    context: models.Context, instance: Instance) -> Iterable[Profile]:
  """Get a list of datafusion Instance dataproc System compute profile."""
  logging.info('fetching dataproc System compute profile list: %s',
               context.project_id)
  system_profiles: List[Profile] = []
  cdap_endpoint = instance.api_endpoint
  datafusion = get_generic.get_generic_api('datafusion', cdap_endpoint)
  response = datafusion.get_system_profiles()
  if response is not None:
    for res in response:
      if (res['provisioner']['name'] == 'gcp-dataproc' or
          res['provisioner']['name'] == 'gcp-existing-dataproc'):
        system_profiles.append(Profile(context.project_id, instance.name, res))
  return system_profiles


@caching.cached_api_call
def get_instance_user_compute_profile(context: models.Context,
                                      instance: Instance) -> Iterable[Profile]:
  """Get a list of datafusion Instance dataproc User compute profile."""
  logging.info('fetching dataproc User compute profile list: %s',
               context.project_id)
  user_profiles: List[Profile] = []
  cdap_endpoint = instance.api_endpoint
  datafusion = get_generic.get_generic_api('datafusion', cdap_endpoint)
  response_namespaces = datafusion.get_all_namespaces()
  if response_namespaces is not None:
    for res in response_namespaces:
      response = datafusion.get_user_profiles(namespace=res['name'])
      if response is not None:
        for res in response:
          if (res['provisioner']['name'] == 'gcp-dataproc' or
              res['provisioner']['name'] == 'gcp-existing-dataproc'):
            user_profiles.append(Profile(context.project_id, instance.name,
                                         res))
      user_profiles = list(filter(bool, user_profiles))
  return user_profiles


@caching.cached_api_call
def extract_datafusion_dataproc_version() -> Dict[str, list[str]]:
  """Extract the supported Data Fusion versions and their corresponding
  Dataproc versions from the GCP documentation."""

  page_url = 'https://cloud.google.com/data-fusion/docs/concepts/configure-clusters'

  try:
    table = html.fetch_and_extract_table(page_url,
                                         tag='h2',
                                         tag_id='version-compatibility')
    if table:
      rows = table.find_all('tr')[1:]  #Skip the header row
      version_dict = {}

      for row in rows:
        cdf_versions = row.find_all('td')[0].get_text().strip()
        dp_versions = row.find_all('td')[1].get_text().strip()

        cdf_versions = cdf_versions.replace(' and later', '')
        cdf_versions_list = []

        if '-' in cdf_versions:
          start, end = map(float, cdf_versions.split('-'))
          while start <= end:
            cdf_versions_list.append(f'{start:.1f}')
            start += 0.1
        else:
          cdf_versions_list.append(cdf_versions)
        dp_versions = [v.split('*')[0].strip() for v in dp_versions.split(',')]
        for version in cdf_versions_list:
          version_dict[version] = dp_versions
      return version_dict

    else:
      return {}
  except (
      requests.exceptions.RequestException,
      AttributeError,
      TypeError,
      ValueError,
      IndexError,
  ) as e:
    logging.error(
        'Error in extracting datafusion and dataproc versions: %s',
        e,
    )
    return {}


class Preference(models.Resource):
  """Represents a Preference."""

  _resource_data: dict

  def __init__(self, project_id, instance, resource_data):
    super().__init__(project_id=project_id)
    self.instance = instance
    self._resource_data = resource_data

  @property
  def full_path(self) -> str:
    """The full path form :

    projects/{project}/locations/{location}/instances/{instance}.
    """
    return self.instance.full_path

  @property
  def image_version(self):
    return self._resource_data.get('system.profile.properties.imageVersion',
                                   None)


def get_system_preferences(context: models.Context,
                           instance: Instance) -> Preference:
  """Get datafusion Instance system preferences."""
  logging.info('fetching dataproc System preferences: %s', context.project_id)
  cdap_endpoint = instance.api_endpoint
  datafusion = get_generic.get_generic_api('datafusion', cdap_endpoint)
  response = datafusion.get_system_preferences()
  return Preference(context.project_id, instance, response)


def get_namespace_preferences(context: models.Context,
                              instance: Instance) -> Mapping[str, Preference]:
  """Get datafusion cdap namespace preferences.
  """
  logging.info('fetching dataproc namespace preferences: %s',
               context.project_id)
  cdap_endpoint = instance.api_endpoint
  datafusion = get_generic.get_generic_api('datafusion', cdap_endpoint)
  namespaces = datafusion.get_all_namespaces()
  namespaces_preferences = {}
  if namespaces is not None:
    for namespace in namespaces:
      response = datafusion.get_namespace_preferences(
          namespace=namespace['name'])
      if bool(response):
        namespaces_preferences[namespace['name']] = Preference(
            context.project_id, instance, response)
  return namespaces_preferences


def get_application_preferences(context: models.Context,
                                instance: Instance) -> Mapping[str, Preference]:
  """Get datafusion cdap application preferences."""
  logging.info('fetching dataproc application preferences: %s',
               context.project_id)
  cdap_endpoint = instance.api_endpoint
  datafusion = get_generic.get_generic_api('datafusion', cdap_endpoint)
  applications_preferences = {}
  namespaces = datafusion.get_all_namespaces()
  if namespaces is not None:
    for namespace in namespaces:
      applications = datafusion.get_all_applications(
          namespace=namespace['name'])
      if applications is not None:
        for application in applications:
          response = datafusion.get_application_preferences(
              namespace=namespace['name'], application_name=application['name'])
          if bool(response):
            applications_preferences[application['name']] = Preference(
                context.project_id, instance, response)
  return applications_preferences
