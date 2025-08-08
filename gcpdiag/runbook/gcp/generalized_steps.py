# Copyright 2023 Google LLC
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
"""Reusable Steps application to any product"""

import typing

import googleapiclient.http
from boltons.iterutils import get_path

from gcpdiag import config, models, runbook
from gcpdiag.models import Resource
from gcpdiag.queries import apis, crm
from gcpdiag.runbook import op
from gcpdiag.runbook.gcp import constants, flags


class HumanTask(runbook.Step):
  """Defines a manual approach verification step involving human intervention.

    This is special step in a runbook designed for situations where automated
    verification is not possible, and human judgment is required. It prompts
    the operator (a human user) to manually check and confirm whether an issue is occurring.
    This can involve accessing a system, reviewing configurations, or validating the state
    of a resource based on provided instructions.
  """
  resource: Resource
  instructions: str = ''
  options: dict = {}

  def __init__(self, uuid=None, parent=None, step_type=op.StepType.MANUAL):
    super().__init__(step_type=step_type, uuid=uuid, parent=parent)

  def execute(self):
    """Human task: Follow the guide below and confirm if issue is occurring or not."""

    instructions = self.instructions or op.prep_msg(op.INSTRUCTIONS_MESSAGE)
    options = self.options or op.DEFAULT_INSTRUCTIONS_OPTIONS
    if instructions:
      response = op.prompt(kind=op.CONFIRMATION,
                           message=instructions,
                           options=options)
      if response == op.UNCERTAIN:
        response = op.add_uncertain(resource=self.resource,
                                    reason=op.prep_msg(op.UNCERTAIN_REASON),
                                    remediation=op.prep_msg(
                                        op.UNCERTAIN_REMEDIATION))
      elif response == op.YES:
        op.add_ok(self.resource, op.prep_msg(op.SUCCESS_REASON))
      elif response == op.NO:
        op.add_failed(self.resource,
                      reason=op.prep_msg(op.FAILURE_REASON),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class ResourceAttributeCheck(runbook.Step):
  """Generalized step used to verify the value of a GCP resource's attribute.

    This step enables the flexible verification of attributes within any JSON-viewable GCP
    resource, such as GCE instances or Cloud Storage buckets. It checks if a specific resource's
    attribute matches an expected value and optionally supports custom evaluation logic for
    more complex verification scenarios.

    Attributes:
      resource_query (Callable): Function to fetch the target GCP resource. Must return
          a `Resource` object. Typically, this is one of the `gcpdiag.queries.*` methods.
      query_kwargs (dict): Keyword arguments to pass to `resource_query`.
      resource (Resource): The GCP resource fetched by `resource_query`.
      attribute (Optional[tuple]): Path to the nested attribute within the resource to be
          verified, represented as a tuple of strings. Utilizes `boltons.iterutils.get_path`
          for navigation.
      evaluator (Optional[Callable]): A custom function for performing complex evaluations
          on a resource attribute.
          Should return a dict:
            {'success_reason': {'key1': 'value1', ...}, 'failure_reason': {...}}
      expected_value (str): The expected value of the target attribute.
      expected_value_type (type): Data type of the expected attribute value. Defaults to `str`.
      extract_args (dict): Configuration for extracting additional information for message
          formatting, with keys specifying the argument name and values specifying the source
          and attribute path.
      message_args (dict): Extracted arguments used for formatting outcome messages.

    Usage:
      An example to check the status of a GCE instance:

      ```python
      status_check = ResourceAttributeCheck()
      status_check.resource_query = gce.get_instance
      status_check.query_kwargs = {
          'project_id': op.get(flags.PROJECT_ID),
          'zone': op.get(flags.ZONE),
          'instance_name': op.get(flags.INSTANCE_NAME)
      }
      status_check.attribute = ('status',)
      status_check.expected_value = 'RUNNING'
      status_check.extract_args = {
          'vm_name': {'source': models.Resource, 'attribute': 'name'},
          'status': {'source': models.Resource, 'attribute': 'status'},
          'resource_project_id': {'source': models.Parameter, 'attribute': 'project_id'}
      }
      ```

    `get_path`: https://boltons.readthedocs.io/en/latest/_modules/boltons/iterutils.html#get_path
  """
  resource_query: typing.Callable
  query_kwargs: dict
  evaluator: typing.Callable
  attribute: tuple
  expected_value: str
  expected_value_type: type = str
  extract_args: dict = {}
  message_args: dict = {}
  template = 'resource_attribute::default'

  resource: Resource

  def execute(self):
    """Verify resource has expected value."""
    try:
      self.resource = self.resource_query(**self.query_kwargs)
      # TODO: change this.
    except googleapiclient.errors.HttpError:
      op.add_uncertain(self.resource,
                       reason=op.prep_msg(op.UNCERTAIN_REASON),
                       remediation=op.prep_msg(op.UNCERTAIN_REMEDIATION))

    if self.extract_args is not None:
      for k, v in self.extract_args.items():
        if v['source'] == Resource:
          # pylint:disable=protected-access
          self.message_args[k] = get_path(self.resource._resource_data,
                                          v['attribute'],
                                          default=v.get('default'))
        if v['source'] == models.Parameter:
          self.message_args[k] = op.get(v['attribute'])

    if hasattr(self, 'evaluator'):
      res = self.evaluator(self.resource)
      if op.SUCCESS_REASON in res:
        kwargs = res.get(op.SUCCESS_REASON) or self.message_args
        op.add_ok(self.resource, op.prep_msg(op.SUCCESS_REASON, **kwargs))
      elif res.get(op.FAILURE_REASON):
        kwargs = res.get(op.FAILURE_REASON) or self.message_args
        op.add_failed(self.resource,
                      reason=op.prep_msg(op.FAILURE_REASON, **kwargs),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION, **kwargs))
    if hasattr(self, 'attribute'):
      # pylint:disable=protected-access
      actual_value = get_path(self.resource._resource_data,
                              self.attribute,
                              default=None)
      if self.expected_value == actual_value:
        op.add_ok(self.resource,
                  op.prep_msg(op.SUCCESS_REASON, **self.message_args))
      else:
        op.add_failed(self.resource,
                      reason=op.prep_msg(op.FAILURE_REASON,
                                         **self.message_args),
                      remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                              **self.message_args))


class ServiceApiStatusCheck(runbook.Step):
  """Check whether or not a service has been enabled for use by a consumer

  Checks is a Cloud API service is enabled or not. Guides the user to enable
  the service if it's expected to be enabled and vice versa.

  Attributes:
      api_name (str): The name of the service to check.
      expected_state (str): The expected state of the service, used to verify
                            against the actual service state retrieved during
                            execution. API state has to be one of the value of
                            gcp.constants.APIState

  """
  api_name: str
  expected_state: constants.APIState
  template: str = 'api::default'
  project_id: str

  def execute(self):
    """Verify {api_name}.{universe_domain} API is {expected_state} in project {project_id}."""
    project = crm.get_project(self.project_id)
    is_enabled = apis.is_enabled(self.project_id, self.api_name)
    service_name = f"{self.api_name}.{config.get('universe_domain')}"
    actual_state = constants.APIState.ENABLED if is_enabled else constants.APIState.DISABLED
    if self.expected_state == actual_state:
      op.add_ok(
          project,
          op.prep_msg(op.SUCCESS_REASON,
                      service_name=service_name,
                      expected_state=self.expected_state.value))
    else:
      remediation = ''
      if self.expected_state == constants.APIState.ENABLED:
        remediation = op.prep_msg(op.FAILURE_REMEDIATION,
                                  service_name=service_name,
                                  project_id=op.get(flags.PROJECT_ID))
      if self.expected_state == constants.APIState.DISABLED:
        remediation = op.prep_msg(op.FAILURE_REMEDIATION_ALT1,
                                  service_name=service_name,
                                  project_id=op.get(flags.PROJECT_ID))
      op.add_failed(project,
                    reason=op.prep_msg(
                        op.FAILURE_REASON,
                        service_name=service_name,
                        expected_state=self.expected_state.value),
                    remediation=remediation)
