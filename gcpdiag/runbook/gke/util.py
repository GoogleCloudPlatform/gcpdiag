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
"""Helpful functions used in different parts of the gke runbooks"""


def is_pod_range_exhausted(ip_space_exhausted_pod_range_log_entries):
  count = len(ip_space_exhausted_pod_range_log_entries)
  pod_range_exhausted = False
  while count:
    log_entry = ip_space_exhausted_pod_range_log_entries.pop()
    if 'GKE_IP_UTILIZATION_POD_RANGES_ALLOCATION_HIGH' in str(log_entry):
      pod_range_exhausted = True
      return pod_range_exhausted
    count -= 1
  return pod_range_exhausted
