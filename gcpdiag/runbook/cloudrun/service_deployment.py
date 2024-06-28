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
"""Contains diagnostic tree for Cloud Run failing to deploy."""
import re
from datetime import datetime

import googleapiclient.errors

from gcpdiag import runbook
from gcpdiag.queries import cloudrun, crm
from gcpdiag.runbook import op
from gcpdiag.runbook.cloudrun import flags


class ServiceDeployment(runbook.DiagnosticTree):
  """Investigates the necessary GCP components searching for reasons for deployment errors.

  This runbook will examine the following key areas:

  1. Container and code Checks.
    - Ensures the Container is in correct state to run in Cloud Run

  Scope of Investigation:
    - Note that this runbook does not provide troubleshooting steps for errors
      caused by the code running in the container.
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      flags.REGION: {
          'type': str,
          'help': 'Region of the service.',
          'required': True
      },
      flags.SERVICE_NAME: {
          'type': str,
          'help': 'Name of the Cloud Run service',
          'required': True,
      },
      flags.START_TIME_UTC: {
          'type': datetime,
          'help': 'Start time of the issue',
      },
      flags.END_TIME_UTC: {
          'type': datetime,
          'help': 'End time of the issue',
      },
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    start = ServiceDeploymentStart()
    self.add_start(start)
    self.add_step(start, ServiceDeploymentCodeStep())


class ServiceDeploymentStart(runbook.StartStep):
  """Prepare the parameters for cloudrun/service-deployment runbook.

  Looks up the cloud run service making sure it exists.
  """

  def execute(self):
    """Verifying context and parameters required for deployment runbook checks."""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    try:
      cloudrun.get_service(op.get(flags.PROJECT_ID), op.get(flags.REGION),
                           op.get(flags.SERVICE_NAME))
    except googleapiclient.errors.HttpError:
      op.add_skipped(
          project,
          reason=f'Service {op.get(flags.SERVICE_NAME)} does not exist in region '
          f'{op.get(flags.REGION)} or project {op.get(flags.PROJECT_ID)}')


class ServiceDeploymentCodeStep(runbook.CompositeStep):
  """Checks for container and code issues."""

  def execute(self):
    """Checking for common container and code issues."""
    self.add_child(ContainerFailedToStartStep())
    self.add_child(ImageWasNotFoundStep())
    self.add_child(NoPermissionForImageStep())


class ContainerFailedToStartStep(runbook.Step):
  """Checks if the deployment error was caused by container failed to start error.

  This step will check if the error is present and link to additional troubleshooting steps.
  """

  template = 'service_deployment::starts_correctly'
  message_re = re.compile(
      r"Revision '[\w-]+' is not ready and cannot serve traffic. The user-provided container "
      r'failed to start and listen on the port defined provided by the PORT=(\d+) environment '
      r'variable.')

  def execute(self):
    """Verifying if there is an error that container failed to start."""
    service = cloudrun.get_service(op.get(flags.PROJECT_ID),
                                   op.get(flags.REGION),
                                   op.get(flags.SERVICE_NAME))
    match = self.message_re.match(service.conditions['RoutesReady'].message)
    if match:
      op.add_failed(service,
                    reason=op.prep_msg(op.FAILURE_REASON, name=service.name),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION))


class ImageWasNotFoundStep(runbook.Step):
  """Checks if if specified image exists.

  This step will check if the error is present and link to additional troubleshooting steps.
  """

  template = 'service_deployment::image_exists'
  message_re = re.compile(
      r"Revision '[\w-]+' is not ready and cannot serve traffic. Image '([^']+)' not found."
  )

  def execute(self):
    """Verifying if specified image exists."""
    service = cloudrun.get_service(op.get(flags.PROJECT_ID),
                                   op.get(flags.REGION),
                                   op.get(flags.SERVICE_NAME))
    match = self.message_re.match(service.conditions['RoutesReady'].message)
    if match:
      op.add_failed(service,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       name=service.name,
                                       image=match.group(1)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            image=match.group(1)))


class NoPermissionForImageStep(runbook.Step):
  """Checks if Cloud Run service agent can fetch the image.

  This step will check if the error is present and link to additional troubleshooting steps.
  """

  template = 'service_deployment::has_permission_for_image'
  message_re = re.compile(
      r"Revision '[\w-]+' is not ready and cannot serve traffic. Google Cloud "
      r'Run Service Agent ([^ ]+) must have permission to read the image, '
      r'([^ ]+).')

  def execute(self):
    """Verifying if Cloud Run service agent can fetch the image."""
    service = cloudrun.get_service(op.get(flags.PROJECT_ID),
                                   op.get(flags.REGION),
                                   op.get(flags.SERVICE_NAME))
    match = self.message_re.match(service.conditions['RoutesReady'].message)
    if match:
      op.add_failed(service,
                    reason=op.prep_msg(op.FAILURE_REASON,
                                       name=service.name,
                                       sa=match.group(1),
                                       image=match.group(2)),
                    remediation=op.prep_msg(op.FAILURE_REMEDIATION,
                                            sa=match.group(1),
                                            image=match.group(2)))
