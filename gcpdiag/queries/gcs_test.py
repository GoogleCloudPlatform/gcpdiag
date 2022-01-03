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
"""Test code in gcs.py."""

from unittest import mock

from gcpdiag import models
from gcpdiag.queries import apis_stub, gcs

DUMMY_PROJECT_NAME = 'gcpdiag-gcs1-aaaa'
DUMMY_BUCKET_NAME = 'b/gcpdiag-gcs1bucket-aaaa'
DUMMY_BUCKET_PERM = 'projectEditor'


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGcs:
  """Test GCS"""

  def test_get_buckets(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    buckets = gcs.get_buckets(context=context)
    assert len(buckets) == 1
    assert DUMMY_BUCKET_NAME in buckets

  def test_get_bucket_iam_policy(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    policy = gcs.get_bucket_iam_policy(context, DUMMY_BUCKET_NAME)
    assert DUMMY_BUCKET_PERM in policy
