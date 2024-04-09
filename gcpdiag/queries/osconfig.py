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

# Lint as: python3
"""Queries related to GCP OS Config"""

import logging
import re
from typing import Dict, Mapping, Optional

import googleapiclient.errors

from gcpdiag import caching, config, models, utils
from gcpdiag.queries import apis


class Inventory(models.Resource):
  """Represents OS Inventory data of a GCE VM instance"""

  _resource_data: dict

  def __init__(self, project_id, resource_data):
    super().__init__(project_id=project_id)
    self._resource_data = resource_data

  # e.g: projects/{project_number}/locations/{location}/instances/{instance_id}/inventory
  @property
  def full_path(self) -> str:
    return self._resource_data['name']

  # e.g: {project_number}/{location}/{instance_id}/inventory
  @property
  def short_path(self) -> str:
    path = self.full_path
    path = re.sub(r'^projects/', '', path)
    path = re.sub(r'/locations/', '/', path)
    path = re.sub(r'/instances/', '/', path)
    return path

  # e.g: debian, windows.
  @property
  def os_shortname(self) -> str:
    if 'osInfo' in self._resource_data:
      return self._resource_data['osInfo'].get('shortName', '')
    return ''

  @property
  def os_version(self) -> str:
    if 'osInfo' in self._resource_data:
      return self._resource_data['osInfo'].get('version', '')
    return ''

  # <key: installed package name, value: installed version>
  @property
  def installed_packages(self) -> Mapping[str, str]:
    installed_packages: Dict[str, str] = {}
    if 'items' in self._resource_data:
      installed_items = [
          i for i in self._resource_data['items'].values()
          if i.get('type', '') == 'INSTALLED_PACKAGE'
      ]
      for item in installed_items:
        if 'installedPackage' not in item:
          continue
        pkg = item['installedPackage']
        if 'yumPackage' in pkg:
          p = pkg['yumPackage']
          installed_packages[p.get('packageName', '')] = p.get('version', '')
        elif 'aptPackage' in pkg:
          p = pkg['aptPackage']
          installed_packages[p.get('packageName', '')] = p.get('version', '')
        elif 'googetPackage' in pkg:
          p = pkg['googetPackage']
          installed_packages[p.get('packageName', '')] = p.get('version', '')
        elif 'windowsApplication' in pkg:
          p = pkg['windowsApplication']
          installed_packages[p.get('displayName',
                                   '')] = p.get('displayVersion', '')
    return installed_packages


@caching.cached_api_call(in_memory=True)
def get_inventory(context: models.Context, location: str,
                  instance_name: str) -> Optional[Inventory]:
  if not apis.is_enabled(context.project_id, 'osconfig'):
    return None
  osconfig_api = apis.get_api('osconfig', 'v1', context.project_id)
  logging.info(
      'fetching inventory data for VM %s in zone %s in project %s',
      instance_name,
      location,
      context.project_id,
  )
  query = (osconfig_api.projects().locations().instances().inventories().get(
      name=
      f'projects/{context.project_id}/locations/{location}/instances/{instance_name}/inventory',
      view='FULL',
  ))
  try:
    resp = query.execute(num_retries=config.API_RETRIES)
  except googleapiclient.errors.HttpError as err:
    if err.resp.status in [404]:
      logging.warning('os inventory info not found for VM instance: %s',
                      instance_name)
      return None
    raise utils.GcpApiError(err) from err
  return Inventory(context.project_id, resource_data=resp)
