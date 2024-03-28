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
"""Globals that will be potentially user-configurable in future."""

import os
import sys
from typing import Any, Dict

import appdirs
import yaml

# gcpdiag version (not configurable, but useful to have here)
VERSION = '0.71-test'
"""
Configuration properties are divided into 3 main categories:
- static (class properties) which values cannot be changed or provided
- options which values can be provided as command arguments
- options which values can be provided as yaml configuration

In addition yaml configuration can contains global configuration which will
be applied to all inspected projects or we can provide strict configuration
dedicated to particular project:

```
---
logging_fetch_max_time_seconds: 300
verbose: 3
within_days: 5

projects:
  myproject:
    billing_project: sample
    include:
    - '*BP*'
    exclude:
    - '*SEC*'
    - '*ERR*'
    include_extended: True
```

Yaml configuration defined per project takes precedence over global
configuration. Global configuration takes precedence over configuration
provided as a command arguments.
"""

#
# Static properties
#

# Default number of retries for API Calls.
API_RETRIES = 10
API_RETRY_SLEEP_MULTIPLIER = 1.4
API_RETRY_SLEEP_RANDOMNESS_PCT = 0.2

_cache_dir = appdirs.user_cache_dir('gcpdiag')


def set_cache_dir(path: str):
  """Set temporary directory for cache."""
  global _cache_dir
  _cache_dir = path


# Cache directory for diskcache.
def get_cache_dir():
  """Get temporary directory for cache."""
  return _cache_dir


# Number of seconds to wait for the gcpdiag.cache API cache lock to be freed.
CACHE_LOCK_TIMEOUT = 120

# How long to cache documents that rarely change (e.g. predefined IAM roles).
STATIC_DOCUMENTS_EXPIRY_SECONDS = 3600 * 24

# Prefetch worker threads
MAX_WORKERS = 10

_args: Dict[str, Any] = {}
_config: Dict[str, Any] = {}
_project_id: str = ''

_defaults: Dict[str, Any] = {
    'auth_adc': False,
    'auth_key': None,
    'billing_project': None,
    'show_skipped': False,
    'hide_ok': False,
    'include': None,
    'exclude': None,
    'include_extended': False,
    'verbose': 0,
    'within_days': 3,
    'hide_skipped': True,
    'show_ok': True,
    'logging_ratelimit_requests': 60,
    'logging_ratelimit_period_seconds': 60,
    'logging_page_size': 500,
    'logging_fetch_max_entries': 10000,
    'logging_fetch_max_time_seconds': 120,
    'enable_gce_serial_buffer': False,
    'auto': False,
    'report_dir': '/tmp/gcpdiag',
    'interface': 'cli'
}

#
# externally used methods
#


def init(args, is_cloud_shell=False):
  """Load configuration based on provided CLI args.

  Args:
      args (Dict): Configuration dictionary.
      project_id (str): Current project id
      is_cloud_shell (bool, optional): Whether cloud shell is used. Defaults to False.
  """
  global _args
  global _config
  _args = args if args else {}
  _args.update({'is_cloud_shell': is_cloud_shell})

  file = args.get('config', None)
  if file:
    # Read the file contents
    if os.path.exists(file):
      with open(file, encoding='utf-8') as f:
        content = f.read()
    else:
      print(f'ERROR: Configuration file: {file} does not exist!',
            file=sys.stderr)
      sys.exit(1)

    # Parse the content of the file as YAML
    if content:
      try:
        _config = yaml.safe_load(content)
      except yaml.YAMLError as err:
        print(f"ERROR: can't parse content of the file as YAML: {err}",
              file=sys.stderr)
        sys.exit(1)


def set_project_id(project_id):
  """Configure project id so that project-id-specific configuration can be retrieved."""
  global _project_id
  _project_id = project_id


def get(key):
  """Find property value for provided key inside CLI args or yaml configuration
  (including global and per project configuration).

  Yaml configuration defined per project takes precedence over global
  configuration. Global configuration takes precedence over configuration
  provided as a command argument.

  Args:
      key (str): property key name

  Returns:
      Any: return value for provided key
  """
  if _project_id and _project_id in _config.get('projects', {}).keys():
    if key in _config['projects'][_project_id].keys():
      # return property from configuration per project if provided
      return _config['projects'][_project_id][key]
  if key in _config:
    # return property from global configuration if provided
    return _config[key]
  if key in _args and _args[key]:
    # return property from args if provided and not None
    return _args[key]
  # return property form defaults
  return _defaults.get(key, None)
