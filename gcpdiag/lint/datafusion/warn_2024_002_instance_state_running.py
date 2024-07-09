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
# Note that we don't have a general rule that checks this for all products,
# because the grant is done lazily, as soon as it is needed. So check that the
# grant is there only when resources of a certain product (like GKE clusters)
# are present, and we know that the grant is necessary for the correct
# operation of that product. Copy the rule for other products, as necessary.
"""Data Fusion instance is in a running state.

Data Fusion instance is not in a running state, The datafusion state is either
Disabled or Failed, The reason for this disabled or Failed state could be due to
configuration errors, KMS key disabled/denied access or key revoked etc...
"""
from gcpdiag import lint, models
from gcpdiag.queries import datafusion

instances_by_project = {}


def prefetch_rule(context: models.Context):
  instances_by_project[context.project_id] = datafusion.get_instances(context)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  instances = instances_by_project[context.project_id]
  if len(instances) == 0:
    report.add_skipped(None, 'no instances found')
  for instance in instances.values():
    if instance.status not in ('FAILED', 'DISABLED'):
      report.add_ok(instance)
    else:
      if instance.status_details is not None:
        report.add_failed(
            instance,
            (f'Instance is in state {instance.status} '
             f'with reason: `{instance.status_details}`'),
        )
      else:
        report.add_failed(instance, f'Instance is in state {instance.status} ')
