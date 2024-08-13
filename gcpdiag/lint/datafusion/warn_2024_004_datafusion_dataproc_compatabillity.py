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
"""Data Fusion version is compatible with Dataproc version from the corresponding compute profiles.

The version of your Cloud Data Fusion environment might not be compatible with
the version of your Dataproc cluster from the corresponding compute profiles.
"""

import re

from packaging import version

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion

projects_instances = {}


def prefetch_rule(context: models.Context):
  projects_instances[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """
    Checks if the datafusion version is compatible with dataproc version
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

  for _, datafusion_instance in sorted(datafusion_instances.items()):
    compute_profiles = []
    # fetch compute profiles of the instance
    compute_profiles.extend(
        datafusion.get_instance_system_compute_profile(context,
                                                       datafusion_instance))
    compute_profiles.extend(
        datafusion.get_instance_user_compute_profile(context,
                                                     datafusion_instance))
    if not compute_profiles:
      report.add_skipped(None, 'No compute profile found')
      return

    datafusion_dataproc_version = datafusion.extract_datafusion_dataproc_version(
    )

    if not datafusion_dataproc_version:
      report.add_skipped(None,
                         "No datafusion and dataproc version's data obtained")

    # Check the autoscaling property
    for profile in compute_profiles:
      if profile.image_version != 'No imageVersion defined':
        dataproc_version = profile.image_version
        dataproc_parsed_version = re.match(r'(\d+\.\d+)', dataproc_version)
        if not dataproc_parsed_version:
          report.add_skipped(
              None, f'Dataproc version : {dataproc_version} is not valid')
          return
        datafusion_version = version.parse(str(datafusion_instance.version))
        version_to_compare = (
            f'{datafusion_version.major}.{datafusion_version.minor}')
        if version_to_compare in datafusion_dataproc_version:
          if (dataproc_parsed_version.group(1)
              in datafusion_dataproc_version[version_to_compare]):
            report.add_ok(
                datafusion_instance,
                f'\n\t{profile}\n\tDatafusion version :'
                f' {datafusion_version}\n\tDataproc version :'
                f' {dataproc_version}\n',
            )
          else:
            report.add_failed(
                datafusion_instance,
                f'\t{profile}\n\tDatafusion version :'
                f' {datafusion_version}\n\tDataproc version :'
                f' {dataproc_version}\n',
            )
      else:
        report.add_ok(datafusion_instance,
                      f'\n\t{profile}\n\t(No imageVersion defined)\n')
