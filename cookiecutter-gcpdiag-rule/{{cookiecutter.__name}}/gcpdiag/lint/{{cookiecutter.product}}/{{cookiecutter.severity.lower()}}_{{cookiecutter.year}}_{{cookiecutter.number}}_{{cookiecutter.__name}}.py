# Copyright {{cookiecutter.year}} Google LLC
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
"""{{cookiecutter.title}}

{{cookiecutter.description}}
"""

from gcpdiag import lint, models


def prepare_rule(context: models.Context):
  # TODO: DELETE/REPLACE this comment and the function's body
  #
  # The prepare_rule() function is an OPTIONAL one and is executed before
  # prefetch_rule() and run_rule(). It is called serially for each lint rule
  # and supposed to be quick to execute
  #
  # Currently the only use-case is for defining/preparing logs queries
  #
  # Example:
  #
  # # logs_by_project is to be defined on the global scope and will be used
  # # in run_rule() later
  # logs_by_project = {}
  # ...
  # # Prepares a log query (the actual query execution happens later)
  # logs_by_project[context.project_id] = logs.query(
  #     project_id=context.project_id,
  #     resource_type='k8s_cluster',
  #     log_name='log_id("events")',
  #     filter_str=f'jsonPayload.message:"{MATCH_STR_1}"'
  # )
  pass


def prefetch_rule(context: models.Context):
  # TODO: DELETE/REPLACE this comment and the function's body
  #
  # The prefetch_rule() function is an OPTIONAL one and is executed after
  # prefetch_rule() and BEFORE run_rule(). It is called in parallel
  # with prefetch_rule() functions defined by other lint rules.
  #
  # It's a good place to fetch/prepare/filter/pre-process data that is going
  # to be used in run_rule(), e.g., to fetch metrics from Cloud Monitoring or
  # some auxiliary data from a relevant GCP API.
  #
  #  Example:
  #
  # # _query_results_per_project_id is to be defined on the global scope and
  # # will be used in run_rule() later
  # _query_results_per_project_id = {}
  # ...
  # # Fetches data from Cloud Monitoring
  # # (the actual query execution happens right here)
  # _query_results_per_project_id[context.project_id] = monitoring.query(
  #     context.project_id, f"""
  # fetch gce_instance
  # | metric 'compute.googleapis.com/guest/disk/bytes_used'
  # | filter metric.device_name == 'sda1'
  # | {within_str}
  # | next_older 5m
  # | filter_ratio_by [resource.instance_id], metric.state == 'free'
  # | every 5m
  # """)
  pass


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # TODO: DELETE/REPLACE this comment and the function's body
  #
  # The run_rule() function is a MANDATORY one. The rule's logic is to be
  # implemented here. All reporting has to be implemented within run_rule()
  #
  # Note: In most cases, there is no need to check if a particular API is
  # enabled or not, as all error handling happens inside the "queries"
  # library and an empty object will be returned if some API is disabled.
  pass
