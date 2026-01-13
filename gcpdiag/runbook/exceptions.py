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
"""Custom exception classes for handling specific errors in the diagnostic process."""


class InvalidDiagnosticTree(Exception):
  """Exception raised for invalid diagnostic tree definition"""

  def __init__(self, message: str):
    super().__init__(message)


class InvalidStepOperation(Exception):
  """Exception raised for invalid operations on a diagnostic step."""

  def __init__(self, message: str):
    super().__init__(message)


class DiagnosticTreeNotFound(Exception):
  """Exception raised when a diagnostic tree cannot be found."""


class DiagnosticTreeConstructionError(Exception):
  """Exception raised for errors during the construction of a diagnostic tree."""

  def __init__(self, message: str):
    super().__init__(message)


class MissingParameterError(ValueError):
  """Raised when a required runbook parameter is missing."""

  def __init__(self,
               message: str,
               missing_parameters_list: list[str] | None = None):
    super().__init__(message)
    self.missing_parameters_list = (missing_parameters_list if
                                    missing_parameters_list is not None else [])


class InvalidParameterError(ValueError):
  """Raised when a runbook parameter is provided but has an invalid value."""


class FailedStepError(Exception):
  """Exception raised for a failed step."""
  pass
