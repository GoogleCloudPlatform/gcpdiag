# Lint as: python3
"""Build and cache GCP APIs"""

from googleapiclient.discovery import build
import functools

@functools.lru_cache(maxsize=None)
def get_api(serviceName, version):
  api = build(serviceName, version, cache_discovery=False)
  return api
