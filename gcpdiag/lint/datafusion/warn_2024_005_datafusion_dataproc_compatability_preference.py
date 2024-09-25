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
"""Data Fusion version is compatible with Dataproc version from the CDAP Preferences settings.

The version of your Cloud Data Fusion environment might not be compatible with
the version of your Dataproc cluster from the CDAP Preferences settings.Check
image version set in the Compute Configurations, Namespace Preferences, or
Pipeline Runtime Arguments.
"""

import re

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion

projects_instances = {}

datafusion_dataproc_version = datafusion.extract_datafusion_dataproc_version()


def prefetch_rule(context: models.Context):
  projects_instances[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks if the datafusion version is compatible with dataproc version

  from the corresponding compute profiles.
  """
  if not apis.is_enabled(context.project_id, 'datafusion'):
    report.add_skipped(
        None,
        'Cloud Data Fusion API is not enabled in'
        f' {crm.get_project(context.project_id)}',
    )
    return

  datafusion_instances = projects_instances[context.project_id]

  if not datafusion_instances:
    report.add_skipped(None, f'no Cloud Data Fusion instances found {context}')
    return

  if not datafusion_dataproc_version:
    report.add_skipped(None,
                       "No datafusion and dataproc version's data obtained")

  for _, datafusion_instance in sorted(datafusion_instances.items()):
    system_preferences = datafusion.get_system_preferences(
        context, datafusion_instance)
    namespace_preferences = datafusion.get_namespace_preferences(
        context, datafusion_instance)
    application_preferences = datafusion.get_application_preferences(
        context, datafusion_instance)
    datafusion_version = datafusion_instance.version
    if application_preferences:
      for (
          application_name,
          application_preference,
      ) in application_preferences.items():
        if application_preference.image_version:
          dataproc_version = application_preference.image_version
          dataproc_valid_version = check_dataproc_version_valid(
              dataproc_version)
          if not dataproc_valid_version:
            report.add_skipped(
                None, f'Dataproc version : {dataproc_version} is not valid')
          else:
            compatible = check_datafusion_dataproc_version_compatibility(
                datafusion_version, dataproc_valid_version)
            if compatible:
              report.add_ok(
                  datafusion_instance,
                  'Application preferences found\npipeline name :'
                  f' {application_name}\n\tDatafusion version :'
                  f' {datafusion_version}\n\tDataproc version :'
                  f' {dataproc_version}\n',
              )
            else:
              report.add_failed(
                  datafusion_instance,
                  'Application preferences found\npipeline name :'
                  f' {application_name}\n\tDatafusion version :'
                  f' {datafusion_version}\n\tDataproc version :'
                  f' {dataproc_version}\n\tCheck Datafusion version is'
                  ' compatible with Dataproc version (VERSION INCOMPATIBILITY'
                  ' FOUND)\n',
              )
    if namespace_preferences:
      for namespace_name, namespace_preference in namespace_preferences.items():
        if namespace_preference.image_version:
          dataproc_version = namespace_preference.image_version
          dataproc_valid_version = check_dataproc_version_valid(
              dataproc_version)
          if not dataproc_valid_version:
            report.add_skipped(
                None, f'Dataproc version : {dataproc_version} is not valid')
          else:
            compatible = check_datafusion_dataproc_version_compatibility(
                datafusion_version, dataproc_valid_version)
            if compatible:
              report.add_ok(
                  datafusion_instance,
                  '\n\tNamespace preferences found'
                  f'\n\tnamespace name : {namespace_name}'
                  '\n\tDatafusion version :'
                  f' {datafusion_version}\n\tDataproc version :'
                  f' {dataproc_version}\n',
              )
            else:
              report.add_failed(
                  datafusion_instance,
                  '\tNamespace preferences found\n\tnamespace name :'
                  f' {namespace_name}\n\tDatafusion version :'
                  f' {datafusion_version}\n\tDataproc version :'
                  f' {dataproc_version}\n\tCheck Datafusion version is'
                  ' compatible with Dataproc version (VERSION INCOMPATIBILITY'
                  ' FOUND)\n',
              )
    if system_preferences.image_version:
      dataproc_version = system_preferences.image_version
      dataproc_valid_version = check_dataproc_version_valid(dataproc_version)
      if not dataproc_valid_version:
        report.add_skipped(
            None, f'Dataproc version : {dataproc_version} is not valid')
      else:
        compatible = check_datafusion_dataproc_version_compatibility(
            datafusion_version, dataproc_valid_version)
        if compatible:
          report.add_ok(
              datafusion_instance,
              '\n\tSystem preferences found\n\tDatafusion version :'
              f' {datafusion_version}\n\tDataproc version :'
              f' {dataproc_version}\n',
          )
        else:
          report.add_failed(
              datafusion_instance,
              '\tSystem preferences found\n\tDatafusion version :'
              f' {datafusion_version}\n\tDataproc version :'
              f' {dataproc_version}\n'
              '\tCheck Datafusion version compatible with Dataproc'
              ' version (VERSION INCOMPATIBILITY FOUND)\n',
          )


def check_dataproc_version_valid(preference_image_version: str):
  dataproc_version = preference_image_version
  dataproc_parsed_version = re.match(r'(\d+\.\d+)', dataproc_version)
  if not dataproc_parsed_version:
    return None
  return dataproc_parsed_version.group(1)


def check_datafusion_dataproc_version_compatibility(
    datafusion_version: version,
    dataproc_version: str,
) -> bool:
  """Checks if the datafusion version is compatible with dataproc version."""
  datafusion_version = version.parse(str(datafusion_version))
  version_to_compare = f'{datafusion_version.major}.{datafusion_version.minor}'
  if version_to_compare in datafusion_dataproc_version:
    if dataproc_version in datafusion_dataproc_version[version_to_compare]:
      return True
  return False
