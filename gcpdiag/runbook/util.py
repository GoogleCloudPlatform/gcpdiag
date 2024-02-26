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
"""Helpful functions used in different parts of the runbook command"""

import random
import re
import string


def generate_random_string(length: int = 4) -> str:
  """Generates a random string of given length."""
  return ''.join(random.choices(string.ascii_letters + string.digits,
                                k=length)).lower()


def camel_to_kebab(camel_case_str: str) -> str:
  """Converts camelCase to kebab-case."""
  return re.sub(r'(?<!^)(?=[A-Z])', '-', camel_case_str).lower()
