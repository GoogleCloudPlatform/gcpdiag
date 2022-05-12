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
"""Queries related to Quota."""

CONSUMER_QUOTA_QUERY_TEMPLATE = """
fetch consumer_quota
| filter resource.service == '{service_name}'
| {{ metric serviceruntime.googleapis.com/quota/allocation/usage
    | align next_older(1d)
    | group_by [resource.project_id, metric.quota_metric, resource.location],
        max(val())
  ; metric serviceruntime.googleapis.com/quota/limit
    | filter metric.limit_name =~ '{limit_name}'
    | align next_older(1d)
    | group_by [resource.project_id, metric.quota_metric, resource.location],
        min(val())
  }}
| join
| value [val(0), val(1)]
| within {within_days}d
| group_by 1d, [max(val(0))/min(val(1)), min(val(1))]
"""
