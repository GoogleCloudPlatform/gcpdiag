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

import importlib
import os
import re
import string
import uuid
from datetime import datetime, timezone

from dateutil import parser
from jinja2 import Environment, FileSystemLoader, select_autoescape

from gcpdiag.runbook import constants

env = Environment(trim_blocks=True,
                  lstrip_blocks=True,
                  autoescape=select_autoescape())

step_outcomes = constants.StepConstants.keys()


def generate_uuid(length: int = 10,
                  separator_interval: int = 4,
                  separator: str = '.'):
  """
  Generates a UUID string with the specified length and separators.

  Args:
      length: The desired length of the final UUID string excluding separators. Default 8
      separator_interval: The number of characters between separators. Default: 4
      separator: uuid separator. Default `.`

  Returns:
      A UUID string formatted with the specified length and separators.
  """
  uuid_str = uuid.uuid4().hex

  if len(uuid_str) > length:
    uuid_str = uuid_str[:length]
  else:
    uuid_str = uuid_str.ljust(length, '0')

  unique_id = separator.join(
      uuid_str[i:i + separator_interval]
      for i in range(0, len(uuid_str), separator_interval))

  return unique_id


def pascal_case_to_kebab_case(s):
  """
  Converts a PascalCase string to kebab-case.

  Args:
      s (str): The string to convert from PascalCase to kebab-case.

  Returns:
      str: The converted string in kebab-case.
  """
  s = re.sub('(.)([A-Z0-9][a-z]+)', r'\1-\2', s)
  s = re.sub('--([A-Z0-9])', r'-\1', s)
  s = re.sub('([a-z])([A-Z0-9])', r'\1-\2', s)
  return s.lower()


def kebab_case_to_pascal_case(s):
  """
  Converts a kebab-case string to PascalCase.

  Args:
      s (str): The string to convert

  Returns:
      str: The converted string in Pascal Case.
  """
  words = s.split('-')
  pascal_str = ''.join(word.capitalize() for word in words)
  return pascal_str


def pascal_case_to_snake_case(s):
  """
  Converts a PascalCase string to snake_case.

  Args:
      s (str): The string to convert from PascalCase to snake_case.

  Returns:
      str: The converted string in snake_case.
  """
  s = re.sub('(.)([A-Z0-9][a-z]+)', r'\1_\2', s)
  s = re.sub('__([A-Z0-9])', r'_\1', s)
  s = re.sub('([a-z])([A-Z0-9])', r'\1_\2', s)
  return s.lower()


def runbook_name_parser(s):
  """
  Converts a string from PascalCase or kebab-case.

  Args:
      s (str): The string to convert from PascalCase to kebab-case.

  Returns:
      str: The converted string in kebab-case
  """
  s = s.replace('_', '-')
  parts = s.split('/')

  return '/'.join([pascal_case_to_kebab_case(part) for part in parts])


def pascal_case_to_title(s):
  """
  Converts a PascalCase string to Title Case (each word's first letter is capitalized).

  Args:
      s (str): The string to convert from PascalCase to Title Case.

  Returns:
      str: The converted string in Title Case.
  """
  s = re.sub('(.)([A-Z0-9][a-z]+)', r'\1 \2', s)
  s = re.sub('__([A-Z0-9])', r' \1', s)
  s = re.sub('([a-z])([A-Z0-9])', r'\1 \2', s)
  return string.capwords(s)


def load_template_block(module_name, file_name, block_name):
  """
  Load specified blocks from a Jinja2 template.

  block_name: Load blocks with this prefixf/
  module_name: Ref to module
  """
  module = importlib.import_module(module_name)

  current_dir = os.path.dirname(os.path.abspath(module.__file__))
  template_file = os.path.join(current_dir, 'templates', f'{file_name}.jinja')

  env.loader = FileSystemLoader(os.path.dirname(template_file))
  template = env.get_template(os.path.basename(template_file))
  observations = {}

  for entry in step_outcomes:
    t_block_name = f'{block_name}_{entry}'
    # Attempt to load each sub-block if it exists within the main block
    if t_block_name in template.blocks:
      observations[entry] = ''.join(template.blocks[t_block_name](
          template.new_context()))
  return observations


def render_template(file_dir,
                    file_name_with_ext,
                    context,
                    block_prefix=None,
                    block_suffix=None):
  """
  Load specified blocks from a Jinja2 template.

  template_path: Path to the Jinja2 template file.
  main_block_name: The main block name to load sub-blocks from.
  sub_block_names: A list of sub-block names to load.
  A dictionary with the loaded block contents.
  """
  env.loader = FileSystemLoader(file_dir)
  context['render_block'] = f'{block_prefix}_{block_suffix}'
  content = env.get_template(f'{file_name_with_ext}').render(context)
  return content


def parse_time_input(time_str):
  """Parse RFC3339, ISO 8601, or epoch time input to datetime object."""
  # Try parsing as a float (epoch timestamp) first
  try:
    epoch = float(time_str)
    return datetime.fromtimestamp(epoch, tz=timezone.utc)
  except ValueError:
    pass  # Not an epoch timestamp

  # Then, try parsing as ISO 8601 / RFC 3339 using dateutil for broader support
  try:
    return parser.isoparse(time_str)
  except ValueError:
    pass
  # Not an ISO 8601 / RFC 3339 formatted date
  # If none of the formats matched, raise an exception
  raise ValueError(f'Date format not recognized: {time_str}')


def resolve_patterns(patterns_str: str, constants_module) -> list[str]:
  """Resolves a ';;' separated string of patterns, handling 'ref:' prefix."""
  patterns = []
  for pattern in patterns_str.split(';;'):
    pattern = pattern.strip()
    if pattern.startswith('ref:'):
      const_name = pattern[4:]
      resolved_value = getattr(constants_module, const_name, None)
      if resolved_value is None:
        raise ValueError(
            f"Could not resolve constant reference: '{pattern}'. "
            f"Ensure '{const_name}' is defined in {constants_module.__name__}.")
      if isinstance(resolved_value, list):
        patterns.extend(resolved_value)
      else:
        patterns.append(resolved_value)
    else:
      patterns.append(pattern)
  return patterns


def get_operator_fn(op_str: str):
  """Maps an operator string to a function from the operator module."""
  operators = {
      'eq': re.match,
      'ne': re.match,
      'lt': re.match,
      'le': re.match,
      'gt': re.match,
      'ge': re.match,
  }
  if op_str not in operators:
    raise ValueError(
        f"Unsupported operator: '{op_str}'. Supported operators are: {list(operators.keys())}"
    )
  return operators[op_str]
