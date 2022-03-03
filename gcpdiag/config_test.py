# Copyright 2022 Google LLC
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
"""Test code in config.py."""

from tempfile import NamedTemporaryFile

from gcpdiag import config

SAMPLE_CONFIG = '''
---
billing_project: sample
include:
- '*BP*'
exclude:
- '*SEC*'
- '*ERR*'
include_extended: True
verbose: 3
within_days: 5
'''

LOGGING_CONFIG = '''
---
logging_ratelimit_requests: 120
logging_ratelimit_period_seconds: 120
logging_page_size: 1000
logging_fetch_max_entries: 20000
logging_fetch_max_time_seconds: 300
'''

EMPTY_CONFIG = ''

PER_PROJECT_CONFIG = '''
---
logging_fetch_max_time_seconds: 300
verbose: 3
within_days: 5

projects:
  myproject:
    billing_project: perproject
    include:
    - '*BP*'
    exclude:
    - '*SEC*'
    - '*ERR*'
    include_extended: True
'''


class Test:
  """Unit tests for Configuration."""

  def test_static_properties(self):
    assert config.CACHE_LOCK_TIMEOUT == 120
    assert config.STATIC_DOCUMENTS_EXPIRY_SECONDS == 3600 * 24
    assert config.MAX_WORKERS == 10

  def test_default_dynamic_properties(self):
    config.init({'project': 'x'}, 'x')
    assert config.get('auth_adc') is False
    assert config.get('include_extended') is False
    assert config.get('config') is None
    assert config.get('verbose') == 0
    assert config.get('within_days') == 3

  def test_overwrite_dynamic_properties(self):
    config.init(
        {
            'project': 'x',
            'auth_adc': True,
            'include_extended': True,
            'verbose': 3,
            'within_days': 7
        }, 'x')
    assert config.get('auth_adc') is True
    assert config.get('include_extended') is True
    assert config.get('verbose') == 3
    assert config.get('within_days') == 7

  def test_include(self):
    config.init({'project': 'x'}, 'x')
    assert config.get('include') is None
    config.init({'project': 'x', 'include': ['*BP*']}, 'x')
    assert config.get('include') == ['*BP*']
    config.init({'project': 'x', 'include': ['*BP*', '*ERR*', '*WARN*']}, 'x')
    assert config.get('include') == ['*BP*', '*ERR*', '*WARN*']

  def test_exclude(self):
    config.init({'project': 'x'}, 'x')
    assert config.get('exclude') is None
    config.init({'project': 'x', 'exclude': ['*BP*']}, 'x')
    assert config.get('exclude') == ['*BP*']
    config.init({'project': 'x', 'exclude': ['*BP*', '*ERR*', '*WARN*']}, 'x')
    assert config.get('exclude') == ['*BP*', '*ERR*', '*WARN*']

  def test_empty_config(self):
    # create temporary config file
    with NamedTemporaryFile() as fp:
      fp.write(EMPTY_CONFIG.encode())
      fp.seek(0)

      # load config from file
      config.init({'project': 'x', 'config': fp.name}, 'x')
      assert config.get('config') == fp.name
      # read value availale only from config
      assert config.get('logging_ratelimit_requests') == 60
      assert config.get('logging_fetch_max_time_seconds') == 120

  def test_sample_config(self):
    # create temporary config file
    with NamedTemporaryFile() as fp:
      fp.write(SAMPLE_CONFIG.encode())
      fp.seek(0)

      # load config from file
      config.init({'project': 'x', 'config': fp.name}, 'x')
      assert config.get('config') == fp.name
      assert config.get('billing_project') == 'sample'
      assert config.get('include_extended') is True
      assert config.get('verbose') == 3
      assert config.get('within_days') == 5
      assert config.get('include') == ['*BP*']
      assert config.get('exclude') == ['*SEC*', '*ERR*']

  def test_logging_config(self):
    # create temporary config file
    with NamedTemporaryFile() as fp:
      fp.write(LOGGING_CONFIG.encode())
      fp.seek(0)

      # load config from file
      config.init({'project': 'x', 'config': fp.name}, 'x')
      assert config.get('config') == fp.name
      assert config.get('logging_ratelimit_requests') == 120
      assert config.get('logging_ratelimit_period_seconds') == 120
      assert config.get('logging_page_size') == 1000
      assert config.get('logging_fetch_max_entries') == 20000
      assert config.get('logging_fetch_max_time_seconds') == 300

  def test_per_project_config(self):
    # create temporary config file
    with NamedTemporaryFile() as fp:
      fp.write(PER_PROJECT_CONFIG.encode())
      fp.seek(0)

      # load config from file
      config.init({'project': 'myproject', 'config': fp.name}, 'myproject')
      assert config.get('config') == fp.name
      assert config.get('billing_project') == 'perproject'
      assert config.get('include_extended') is True
      assert config.get('include') == ['*BP*']
      assert config.get('exclude') == ['*SEC*', '*ERR*']

      assert config.get('verbose') == 3
      assert config.get('logging_fetch_max_time_seconds') == 300
      assert config.get('within_days') == 5
