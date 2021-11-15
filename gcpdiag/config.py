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

import appdirs

# gcpdiag version (not configurable, but useful to have here)
VERSION = '0.48'

# Default number of retries for API Calls.
API_RETRIES = 10

# Cache directory for diskcache.
CACHE_DIR = appdirs.user_cache_dir('gcpdiag')

# Number of seconds to wait for the gcpdiag.cache API cache lock to be freed.
CACHE_LOCK_TIMEOUT = 120

# How long to cache documents that rarely change (e.g. predefined IAM roles).
STATIC_DOCUMENTS_EXPIRY_SECONDS = 3600 * 24

# How far back to look for metrics and logs
WITHIN_DAYS = 3

# Logging-related parameters
LOGGING_PAGE_SIZE = 500
LOGGING_FETCH_MAX_ENTRIES = 10000
LOGGING_FETCH_MAX_TIME_SECONDS = 120
# https://cloud.google.com/logging/quotas:
LOGGING_RATELIMIT_REQUESTS = 60
LOGGING_RATELIMIT_PERIOD_SECONDS = 60

# Prefetch worker threads
MAX_WORKERS = 10

# Authentication method (set via command-line arguments)
AUTH_METHOD = 'oauth'
AUTH_KEY = None
