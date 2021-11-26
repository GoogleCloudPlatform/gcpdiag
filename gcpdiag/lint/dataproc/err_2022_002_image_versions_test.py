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
"""Test code in dataproc.py."""

from gcpdiag.lint.dataproc.err_2022_002_image_versions import ImageVersion


class TestDataprocImageVersions:
  """Test deprecated version detection"""

  def dotest(self, versions, expected):
    for v in versions:
      assert ImageVersion(v).is_deprecated() is expected

  def test_not_deprecated(self):
    self.dotest(['2.0.24-debian10', '2.0-debian10'], False)

  def test_deprecated(self):
    self.dotest(['1.2.3-debian10', '1.2-debian10'], True)

  def test_something_completely_wrong(self):
    self.dotest(['something'], False)

  def test_something_close_but_wrong_parts(self):
    self.dotest(['2.x.24-debian10', 'x.0.24-debian10', '2.0.x-debian10'], False)

  def test_missing_parts(self):
    self.dotest([
        '2', '2.0', '2.0.24', '2.0.24-42', '2.0.24-msdos', '.0.24-msdos42',
        '2.0.-msdos42'
    ], False)
