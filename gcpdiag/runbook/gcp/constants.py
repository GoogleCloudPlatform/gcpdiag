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
"""Common constants available at gcp platform level"""
from enum import Enum


class APIState(Enum):
  """Enum for representing the state of a service API.

  Attributes:
    STATE_UNSPECIFIED: The default value, indicating that the enabled state of the service is
                       unspecified or not meaningful. This state is typical for consumers other
                       than projects (such as folders and organizations),
                       where the enabled state is always considered unspecified.
    DISABLED: Indicates that the service cannot be used by the consumer.
              It represents a service that has either been
              explicitly disabled or has never been enabled.
    ENABLED: Indicates that the service has been explicitly enabled for use by the consumer.
  """
  STATE_UNSPECIFIED = 'STATE_UNSPECIFIED'
  DISABLED = 'DISABLED'
  ENABLED = 'ENABLED'


GCP_SYSTEM_EMAIL = 'system@google.com'
