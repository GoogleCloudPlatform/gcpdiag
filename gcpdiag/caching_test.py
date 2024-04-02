# Copyright 2024 Google LLC
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
"""Test code in caching.py."""

import secrets
import string
import threading
import unittest

from gcpdiag import caching


def simple_function(mixer_arg):
  # Generate a unique string of 10 characters
  return mixer_arg.join(
      secrets.choice(string.ascii_letters + string.digits) for _ in range(10))


# Decorated versions of the simple_function for in-memory and disk cache testing
cached_in_memory = caching.cached_api_call(in_memory=True)(simple_function)
cached_on_disk = caching.cached_api_call(simple_function)


class CacheBypassTests(unittest.TestCase):
  """Testing cache bypass test"""

  def test_cache_bypass_in_memory(self):
    with caching.bypass_cache():
      result_cached = cached_in_memory('same-arg')
    self.assertIsInstance(result_cached, str)
    # Another call not bypassing the cache should return originally cached result
    result_cached_two = cached_in_memory('same-arg')
    # String should be the same given bypass is not turned on
    self.assertEqual(result_cached, result_cached_two)
    # memory id should be the same
    self.assertEqual(id(result_cached), id(result_cached_two))

    with caching.bypass_cache():
      result_bypass = cached_in_memory('same-arg')
    self.assertNotEqual(result_cached, result_bypass)

    result_after_bypass = cached_in_memory('same-arg')
    self.assertNotEqual(result_cached, result_after_bypass)

  def test_cache_bypass_disk_cache(self):
    with caching.bypass_cache():
      result_cached = cached_on_disk('same-arg')
    self.assertIsInstance(result_cached, str)

    # Another call should return originally cached result
    result_cached_two = cached_on_disk('same-arg')
    self.assertEqual(result_cached, result_cached_two)

    with caching.bypass_cache():
      result_bypass = cached_on_disk('same-arg')
    self.assertNotEqual(result_cached, result_bypass)

    result_after_bypass = cached_on_disk('same-arg')
    self.assertNotEqual(result_cached, result_after_bypass)

  def test_thread_safe_caching(self):
    results = set()

    def worker(arg, result):
      with caching.bypass_cache():
        result = cached_on_disk(arg)
      results.add(result)

    threads = [
        threading.Thread(target=worker, args=(
            arg,
            results,
        )) for arg in ['a', 'a', 'b', 'c']
    ]
    for t in threads:
      t.start()
      t.join()
    self.assertEqual(len(results), 4, 'All threads should get different result')
