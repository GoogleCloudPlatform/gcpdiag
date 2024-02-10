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

FAILURE_REASON = 'failure_reason'
FAILURE_REMEDIATION = 'failure_remediation'
SUCCESS_REASON = 'success_reason'
UNCERTAIN_REASON = 'uncertain_reason'
UNCERTAIN_REMEDIATION = 'uncertain_remediation'
SKIPPED_REASON = 'skipped_reason'
STEP_MESSAGE = 'step_message'

INSTRUCTIONS_MESSAGE = 'instruction_message'
INSTRUCTIONS_CHOICE_OPTIONS = 'instructions_choice_options'


class StepType(Enum):
  """Types of Diagnotic Tree Steps"""
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
