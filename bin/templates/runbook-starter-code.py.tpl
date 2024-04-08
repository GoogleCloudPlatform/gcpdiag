# Copyright [YEAR] Google LLC
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

"""TODO: Overview of classes contained in file"""

from datetime import datetime

from gcpdiag import runbook
from gcpdiag.runbook import op
from gcpdiag.queries import crm, gce, gke, iam, logs, pubsub
from gcpdiag.runbook.gce import flags
from gcpdiag.runbook.iam import generalized_steps as iam_gs

CUSTOM_FLAG = 'custom_flag'


class TreeName(runbook.DiagnosticTree):
  """TODO: Single line explaining runbook's purpose.

  Overview message for end user alignment with runbook capabilities

  - Subheading: We check X product domain
  - Subheading: We check Y product domain
  - ...
  """
  parameters = {
      flags.PROJECT_ID: {
          'type': str,
          'help': 'The Project ID of the resource under investigation',
          'required': True
      },
      CUSTOM_FLAG: {
          'type': str,
          'help': 'Help text for the parameter',
          'default': 'gce'
      }
  }

  def build_tree(self):
    """Construct the diagnostic tree with appropriate steps."""
    # Instantiate your step classes
    start = TreeNameStart()
    # add them to your tree
    self.add_start(start)
    # you can create custom steps to define unique logic
    custom = CustomStep()
    # Describe the step relationships
    self.add_step(parent=start, child=custom)
    # Type of steps: a Gateway i.e Decision point.
    self.add_step(parent=custom, child=TreeNameGateway())
    # Type of steps: a composite step i.e a group of related steps
    self.add_step(parent=custom, child=TreeNameCompositeStep())
    # Ending your runbook
    self.add_end(TreeNameEnd())


class TreeNameStart(runbook.StartStep):
  """TODO: Write a one line overview of this step

  Detailed explanation of how this works and what it checks.
  """

  def execute(self):
    """TODO: One line string for the checks being performed by start step"""
    proj = crm.get_project(op.get(flags.PROJECT_ID))
    if proj:
      op.info(f'name: {proj.name}, id: {proj.id}, number: {proj.number}')
    product = self.__module__.split('.')[-2]
    op.put(CUSTOM_FLAG, product)


class CustomStep(runbook.Step):
  """TODO: Write a one line overview of this step

  Detailed explanation of how this works and what it checks.
  """

  def _project_helper(self, project):
    return project.id == project.name

  def execute(self):
    """TODO: One line string for the checks being performed by custom step"""
    project = crm.get_project(op.get(flags.PROJECT_ID))
    if self._project_helper(project):
      op.add_ok(
          project,
          reason='Nice! your project has the same string for name and id')
    else:
      op.add_failed(project,
                         reason='Your project name and id are different',
                         remediation='different name and id is fine too. ')


class TreeNameGateway(runbook.Gateway):
  """TODO: Write a one line overview of this this decision point

  Detailed explanation of how this works and what it checks.
  """

  def execute(self):
    """TODO: One line string for the decision being performed at this split point..."""
    # Decision points.
    if op.get(CUSTOM_FLAG) == 'gce':
      num = len(gce.get_instances(op.context))
      op.info(f'Your project has {num} GCE instance{"" if num==1 else "s"} 🔥')
    elif op.get(CUSTOM_FLAG) == 'gke':
      num = len(gke.get_clusters(op.context))
      op.info(f'Your project has {num} GKE cluster{"" if num==1 else "s"} 🔥')
    elif op.get(CUSTOM_FLAG) == 'pubsub':
      num = len(pubsub.get_topics(op.context))
      op.info(f'Your project has {num} Pubsub Topic{"" if num==1 else "s"} 🔥')
    else:
      num = len(iam.get(op.context.project_id))
      op.info(f'Your project has {num} service account{"" if num==1 else "s"} 🔥')


class TreeNameCompositeStep(runbook.CompositeStep):
  """TODO: Write a one line overview of this composite step

  Explain the collection of steps in a composite step
  """

  def execute(self):
    """TODO: One line string for the collection of step grouped in this Composite Step..."""
    using_a_generalized_class = iam_gs.IamPolicyCheck()
    using_a_generalized_class.permissions = ['test.perm.one', 'test.perm.two']
    using_a_generalized_class.principal = 'user:user_one@example.com'
    using_a_generalized_class.require_all = False
    self.add_child(using_a_generalized_class)

    using_another_generalized_class = iam_gs.IamPolicyCheck(name='unique_name')
    using_another_generalized_class.roles = [
        'roles/test.one', 'role/test.two'
    ]
    using_another_generalized_class.principal = 'user:user_two@example.com'
    using_another_generalized_class.require_all = True
    self.add_child(using_another_generalized_class)


class TreeNameEnd(runbook.EndStep):
  """TODO: Write a one line overview of this end step

  TODO: Explain the the checks done by the end step whether automatic assessment or manual.
  """

  def execute(self):
    """TODO: Write checks being performed by end step"""
    log_entries = logs.realtime_query(
        project_id=op.get(flags.PROJECT_ID),
        filter_str=f'log_name=~"projects/{op.get(flags.PROJECT_ID)}"',
        start_time_utc=datetime.now(),
        end_time_utc=op.get(flags.END_TIME_UTC))
    if log_entries:
      op.info((f'You\'ve got new logs in {op.get(flags.PROJECT_ID)} ',
                    f'since {op.get(flags.END_TIME_UTC)} 🚀'))
    else:
      op.info(f'No new logs in {op.get(flags.PROJECT_ID)} '
                   f'since {op.get(flags.END_TIME_UTC)} 😎. Nice!')


# TODO: Remove all template boilerplate before submitting your runbook.
