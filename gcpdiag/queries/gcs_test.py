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
DUMMY_BUCKET_PATH = 'b/gcpdiag-gcs1bucket-aaaa'
DUMMY_BUCKET_NAME = 'gcpdiag-gcs1bucket-aaaa'
DUMMY_BUCKET_WITH_RETENTION_NAME = 'gcpdiag-gcs1bucket2-aaaa'
DUMMY_BUCKET_PERM = 'projectEditor:gcpdiag-gcs1-aaaa'
DUMMY_BUCKET_LABELS = {
    'gcpdiag-gcs1bucket-aaaa': {},
    'gcpdiag-gcs1bucket-labels-aaaa': {
        'label1': 'value1'
    },
}
FAKE_BUCKET_RESOURCE_DATA = {
    'kind':
        'storage#bucket',
    'selfLink':
        'https://www.googleapis.com/storage/v1/b/gcpdiag-gcs1bucket-aaaa',
    'id':
        'gcpdiag-gcs1bucket-aaaa',
    'name':
        'gcpdiag-gcs1bucket-aaaa',
    'projectNumber':
        '12340008',
    'metageneration':
        '9',
    'location':
        'US',
    'storageClass':
        'STANDARD',
    'etag':
        'CAE=',
    'timeCreated':
        '2016-07-12T15:05:45.473Z',
    'updated':
        '2022-06-22T10:25:28.219Z',
    'locationType':
        'multi-region',
    'rpo':
        'DEFAULT'
}


@mock.patch('gcpdiag.queries.apis.get_api', new=apis_stub.get_api_stub)
class TestGcs:
  """Test GCS"""

  def test_get_buckets(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    buckets = gcs.get_buckets(context=context)
    assert len(buckets) == 3
    assert DUMMY_BUCKET_NAME in buckets

  def test_get_bucket_iam_policy(self):
    policy = gcs.get_bucket_iam_policy(DUMMY_PROJECT_NAME, DUMMY_BUCKET_PATH)
    assert DUMMY_BUCKET_PERM in policy.get_members()

  def test_bucket_labels(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    buckets = gcs.get_buckets(context=context)
    for bucket_name, labels in DUMMY_BUCKET_LABELS.items():
      assert buckets[bucket_name].labels == labels

  def test_get_bucket_with_retention(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    bucket = gcs.get_bucket(context=context,
                            bucket=DUMMY_BUCKET_WITH_RETENTION_NAME)
    assert bucket.retention_policy.retention_period == 10

  def test_get_uniform_access(self):
    context = models.Context(project_id=DUMMY_PROJECT_NAME)
    bucket = gcs.get_bucket(context=context,
                            bucket=DUMMY_BUCKET_WITH_RETENTION_NAME)
    assert bucket.is_uniform_access() is False
    fake_bucket = gcs.Bucket(project_id=DUMMY_PROJECT_NAME,
                             resource_data=FAKE_BUCKET_RESOURCE_DATA)
    assert fake_bucket.is_uniform_access() is False
