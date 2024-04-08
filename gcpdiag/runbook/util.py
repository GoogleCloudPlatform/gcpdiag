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
import random
import re
import string
import sys
from datetime import datetime, timezone

from dateutil import parser
from jinja2 import Environment, FileSystemLoader, select_autoescape

from gcpdiag.runbook import constants

env = Environment(trim_blocks=True,
                  lstrip_blocks=True,
                  autoescape=select_autoescape())

step_outcomes = constants.StepConstants.keys()


def generate_random_string(length: int = 4) -> str:
  """Generates a random string of given length."""
  return ''.join(random.choices(string.ascii_letters + string.digits,
                                k=length)).lower()


def pascal_case_to_kebab_case(s):
  """
  Converts a PascalCase string to kebab-case.

  Args:
      s (str): The string to convert from PascalCase to kebab-case.

  Returns:
      str: The converted string in kebab-case.
  """
  return re.sub(r'(?<!^)(?=[A-Z])', '-', s).lower()


def pascal_case_to_snake_case(s):
  """
  Converts a PascalCase string to snake_case.

  Args:
      s (str): The string to convert from PascalCase to snake_case.

  Returns:
      str: The converted string in snake_case.
  """
  return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()


def runbook_name_parser(s):
  """
  Converts a string from PascalCase or kebab-case to snake_case.

  Args:
      s (str): The string to convert from PascalCase or kebab-case to snake_case.

  Returns:
      str: The converted string in snake_case
  """
  s = s.replace('_', '-')
  # Convert PascalCase to snake_case
  s = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s).lower()
  return s


def pascal_case_to_title(s):
  """
  Converts a PascalCase string to Title Case (each word's first letter is capitalized).

  Args:
      s (str): The string to convert from PascalCase to Title Case.

  Returns:
      str: The converted string in Title Case.
  """
  words = re.sub(r'(?<!^)(?=[A-Z])', ' ', s).lower()
  return words.title()


def load_template_block(module_name, file_name, block_name):
  """
  Load specified blocks from a Jinja2 template.

  block_name: Load blocks with this prefix
  module_name: Ref to module
  """
  module = importlib.import_module(module_name)

  current_dir = os.path.dirname(os.path.abspath(module.__file__))
  template_file = os.path.join(current_dir, 'templates', f'{file_name}.jinja')

  env.loader = FileSystemLoader(os.path.dirname(template_file))
  template = env.get_template(os.path.basename(template_file))
  prompts = {}

  for entry in step_outcomes:
    t_block_name = f'{block_name}_{entry}'
    # Attempt to load each sub-block if it exists within the main block
    if t_block_name in template.blocks:
      prompts[entry] = ''.join(template.blocks[t_block_name](
          template.new_context()))
  return prompts


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


# pylint: disable=protected-access
def get_caller_object(index: int):
  # Attempt to get the 'self' variable from the caller's frame.
  # plus one for this current method
  return sys._getframe(index + 1).f_locals.get('self')
