# Copyright 2025 Google LLC
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
"""Abstract interface for providing execution context."""

import abc


class ContextProvider(abc.ABC):
  """Abstract interface for managing execution context for threads."""

  @abc.abstractmethod
  def setup_thread_context(self) -> None:
    """Set up the necessary context for the current thread."""
    pass

  @abc.abstractmethod
  def teardown_thread_context(self) -> None:
    """Clean up the thread context."""
    pass
