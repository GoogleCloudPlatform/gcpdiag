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

# Lint as: python3
"""Runbook utility."""
import json
import re
from datetime import datetime, timezone


def search_pattern_in_serial_logs(patterns, contents, operator='OR'):
  pattern = ''
  if operator == 'OR':
    pattern = ' | '.join(patterns)
  elif operator == 'AND':
    pattern_arr = [re.compile(fr'{string}') for string in patterns]
    if all(p.search(contents) for p in pattern_arr):
      return True
  regex = re.compile(pattern, re.MULTILINE | re.IGNORECASE)
  result = regex.search(contents)
  if result:
    return True
  return False


def user_has_valid_ssh_key(local_user, keys, key_type=None) -> bool:
  """Given a list of keys, check if it has *at least one* valid SSH
   key for the local_user. A key is valid if:
    - the local_user matches the key username
    - a the key type matches if specified.
    - key is not expired if present

  return:
    True if at least one valid key or False if none is valid
   """
  pattern = r'(?P<user>\w+):(?P<type>[\w-]+) \S+(?: \S+|)(?: google-ssh {"userName":"\S+","expireOn":"(?P<expire_on>[^"]+)"}|$)'  # pylint:disable=line-too-long
  # patten the input string into key_value and if formated the ssh info
  for key in keys:
    key = key.strip()
    m = re.search(pattern, key)
    # Check if 'testuser' is in the user_info and 'google-ssh' is in the ssh_info
    # TODO: Check later if keyname and username can be different in an SSH key.
    if m:
      valid = local_user == m.group('user')
      # Check expected key_type is the same as what's in the keyvalue
      if key_type:
        valid = key_type == m.group('type')
      if valid:
        return valid
  return False
