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
"""Common constants used within runbook"""
from enum import Enum

# Messaging Scenarios
FAILURE_REASON = 'failure_reason'
FAILURE_REMEDIATION = 'failure_remediation'
SUCCESS_REASON = 'success_reason'
UNCERTAIN_REASON = 'uncertain_reason'
UNCERTAIN_REMEDIATION = 'uncertain_remediation'
SKIPPED_REASON = 'skipped_reason'
STEP_NAME = 'step_name'

FAILURE_REASON_ALT1 = f'{FAILURE_REASON}_a1'
FAILURE_REMEDIATION_ALT1 = f'{FAILURE_REMEDIATION}_a1'
SUCCESS_REASON_ALT1 = f'{SUCCESS_REASON}_a1'
UNCERTAIN_REASON_ALT1 = f'{UNCERTAIN_REASON}_a1'
UNCERTAIN_REMEDIATION_ALT1 = f'{UNCERTAIN_REMEDIATION}_a1'
SKIPPED_REASON_ALT1 = f'{SKIPPED_REASON}_a1'
STEP_NAME_ALT1 = f'{STEP_NAME}_a1'

FAILURE_REASON_ALT2 = f'{FAILURE_REASON}_a2'
FAILURE_REMEDIATION_ALT2 = f'{FAILURE_REMEDIATION}_a2'
SUCCESS_REASON_ALT2 = f'{SUCCESS_REASON}_a2'
UNCERTAIN_REASON_ALT2 = f'{UNCERTAIN_REASON}_a2'
UNCERTAIN_REMEDIATION_ALT2 = f'{UNCERTAIN_REMEDIATION}_a2'
SKIPPED_REASON_ALT2 = f'{SKIPPED_REASON}_a2'
STEP_NAME_ALT2 = f'{STEP_NAME}_a2'

FAILURE_REASON_ALT3 = f'{FAILURE_REASON}_a3'
FAILURE_REMEDIATION_ALT3 = f'{FAILURE_REMEDIATION}_a3'
SUCCESS_REASON_ALT3 = f'{SUCCESS_REASON}_a3'
UNCERTAIN_REASON_ALT3 = f'{UNCERTAIN_REASON}_a3'
UNCERTAIN_REMEDIATION_ALT3 = f'{UNCERTAIN_REMEDIATION}_a3'
SKIPPED_REASON_ALT3 = f'{SKIPPED_REASON}_a3'
STEP_NAME_ALT3 = f'{STEP_NAME}_a3'

INSTRUCTIONS_MESSAGE = 'instructions_message'
STEP_LABEL = 'label'
INSTRUCTIONS_CHOICE_OPTIONS = 'instructions_choice_options'
DEFAULT_INSTRUCTIONS_OPTIONS = {
    'y': 'Yes, Issue is not happening',
    'n': 'No, Issue is occuring',
    'u': 'Unsure'
}
RCA = 'rca'

StepConstants = {
    STEP_LABEL:
        'The Label used in DT images',
    STEP_NAME:
        'The introduction message displayed to user describing what the step does.',
    FAILURE_REASON:
        'The failure reason for this step.',
    FAILURE_REMEDIATION:
        'How to solve the main failure scenario.',
    SUCCESS_REASON:
        'The reason why this step is consider to be a success.',
    UNCERTAIN_REASON:
        'The reason why this step is uncertain of the outcome.',
    UNCERTAIN_REMEDIATION:
        'How to address uncertainty in the outcome.',
    SKIPPED_REASON:
        'The reason why this step was skipped.',
    FAILURE_REASON_ALT1:
        'The failure reason for Scenario 1 step.',
    FAILURE_REMEDIATION_ALT1:
        'How to solve the main failure scenario in Scenario 1.',
    SUCCESS_REASON_ALT1:
        'The reason why Scenario 1 is considered a success.',
    UNCERTAIN_REASON_ALT1:
        'The reason for uncertainty in the Scenario 1 outcome.',
    UNCERTAIN_REMEDIATION_ALT1:
        'How to address uncertainty in the Scenario 1 outcome.',
    SKIPPED_REASON_ALT1:
        'The reason why Scenario 1 was skipped.',
    FAILURE_REASON_ALT2:
        'The failure reason for Scenario 2 step.',
    FAILURE_REMEDIATION_ALT2:
        'How to solve the main failure scenario in Scenario 2.',
    SUCCESS_REASON_ALT2:
        'The reason why Scenario 2 is considered a success.',
    UNCERTAIN_REASON_ALT2:
        'The reason for uncertainty in the Scenario 2 outcome.',
    UNCERTAIN_REMEDIATION_ALT2:
        'How to address uncertainty in the Scenario 2 outcome.',
    SKIPPED_REASON_ALT2:
        'The reason why Scenario 2 was skipped.',
    FAILURE_REASON_ALT3:
        'The failure reason for Scenario 3 step.',
    FAILURE_REMEDIATION_ALT3:
        'How to solve the main failure scenario in Scenario 3.',
    SUCCESS_REASON_ALT3:
        'The reason why Scenario 3 is considered a success.',
    UNCERTAIN_REASON_ALT3:
        'The reason for uncertainty in the Scenario 3 outcome.',
    UNCERTAIN_REMEDIATION_ALT3:
        'How to address uncertainty in the Scenario 3 outcome.',
    SKIPPED_REASON_ALT3:
        'The reason why Scenario 3 was skipped.',
    INSTRUCTIONS_MESSAGE:
        'Instruction on a manual task.',
    INSTRUCTIONS_CHOICE_OPTIONS:
        'Options available in this manual task.',
    RCA:
        'Root cause analysis.'
}


class StepType(Enum):
  """Types of Diagnostic Tree Steps"""
  START = 'START'
  END = 'END'
  AUTOMATED = 'AUTOMATED STEP'
  COMPOSITE = 'COMPOSITE STEP'
  MANUAL = 'MANUAL STEP'
  PARAMETER = 'PARAMETER PREP'
  GATEWAY = 'GATEWAY'

  @classmethod
  def to_list(cls):
    return list(map(lambda c: c.value, cls))


END_MESSAGE = (
    'Before reaching out to Google Cloud Support: \n'
    '1. Thoroughly investigate '
    'the issue with the most appropriate team within your organization. Many issues can be '
    'resolved internally and fall within the scope of your operational responsibilities:'
    'https://cloud.google.com/architecture/framework/security'
    '/shared-responsibility-shared-fate\n\n'
    '2. If your internal investigation suggests that the issue is related to the '
    'Google Cloud Platform and requires intervention by Google engineers, please '
    'contact Google Cloud Support for further assistance.\n\n'
    '3. View our Google Cloud Service Health Dashboard to know what issues are already know'
    'and currently being resolved:\n'
    'https://cloud.google.com/support/docs/customer-care-procedures#view_known_issues\n\n'
    '4. If you still need further assistance contact customer care:\n'
    'https://cloud.google.com/support/docs/customer-care-procedures#contact_customer_care\n\n'
    'Recommended Action: When submitting a support ticket, please include the generated '
    'report to facilitate a quicker resolution by the Google Cloud support team.'
    'For more information on how to get the best out of our support services visit:\n'
    'https://cloud.google.com/support/docs/customer-care-procedures\n\n')

BOOL_VALUES = {
    'y': True,
    'yes': True,
    'true': True,
    '1': True,
    'n': False,
    'no': False,
    'false': False,
    '0': False,
    'none': False
}

RETEST = 'RETEST'
YES = 'YES'
NO = 'NO'
UNCERTAIN = 'UNCERTAIN'
CONTINUE = 'CONTINUE'
CONFIRMATION = 'CONFIRMATION'
STOP = 'STOP'
STEP = StepType.to_list()
DECISION = 'DECISION'
HUMAN_TASK = 'Choose the next action'
HUMAN_TASK_OPTIONS = {
    'r': 'Retest current step',
    'c': 'Continue',
    's': 'Stop Runbook'
}
CONFIRMATION_OPTIONS = {'Yes/Y/y': 'Yes', 'No/N/n': 'No'}
GENERATE_REPORT = 'GENERATE_REPORT'
STATUS_ORDER = ['failed', 'uncertain', 'ok', 'skipped']
FINALIZE_INVESTIGATION = 'FINALIZE_INVESTIGATION'

CLI = 'cli'
API = 'api'

# Restricted attributes that should never be used in observations and tep naming
RESTRICTED_ATTRIBUTES = {
    'uuid', 'steps', 'observations', 'product', 'doc_file_name', 'type',
    'template'
}
