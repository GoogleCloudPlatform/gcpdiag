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
"""Scaling down is disabled for the Compute Profile for Dataproc.

Autoscaling is not recommended for scaling down. Decreasing the cluster
size with autoscaling removes nodes that hold intermediate data, which might
cause your pipelines to run slowly or fail in datafusion.
"""
import re

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, datafusion, dataproc

projects_instances = {}


def prefetch_rule(context: models.Context):
  projects_instances[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  """Checks if the autoscaling down is enabled for the compute profile."""
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

    #Check the autoscaling property
    for profile in compute_profiles:
      if profile.autoscaling_enabled:
        report.add_ok(datafusion_instance, f'\n\t{profile}\n')
      elif profile.auto_scaling_policy != 'No autoScalingPolicy defined':
        uri = profile.auto_scaling_policy
        match = re.match(
            r'projects/([^/]+)/regions/([^/]+)/autoscalingPolicies/([^/]+)',
            uri)
        if match:
          project_id = match.group(1)
          region = match.group(2)
          policy_id = match.group(3)
          policy = dataproc.get_auto_scaling_policy(project_id, region,
                                                    policy_id)
          if policy.scale_down_factor != 0.0:
            report.add_failed(datafusion_instance,
                              f'  {profile} : autoscaling down enabled\n')
          else:
            report.add_ok(datafusion_instance, f'\n\t{profile}\n')
      else:
        report.add_ok(datafusion_instance, f'\n\t{profile}\n')
