# Lint as: python3
"""Build and cache GCP APIs"""

import functools

from googleapiclient.discovery import build

RETRIES = 2


@functools.lru_cache(maxsize=None)
def get_api(service_name: str, version: str):
  api = build(service_name, version, cache_discovery=False)
  return api
