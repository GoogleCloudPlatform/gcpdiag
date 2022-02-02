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
"""Dataproc cluster doesn't use deprecated images

We should expect problems if cluster runs one of the known deprecated and unsupported images.
"""

import re

from gcpdiag import lint, models
from gcpdiag.queries import dataproc

clusters_by_project = {}


class VersionParser:
  """
  Example: 2.0.24-debian10
  """

  def __init__(self, s):
    self.str = s
    self.match = None
    self.matches_format = False
    self.major = None
    self.minor = None
    self.os = None
    self.os_ver = None

  def parse(self):
    self.match_re()
    if not self.match:
      return
    self.fill_properties_from_match()

  def match_re(self):
    self.match = re.match((r'^(?P<major>\d+).(?P<minor>\d+)(?:.\d+)?'
                           r'(?:-(?P<os_n>[a-zA-Z]+)?(?P<os_v>\d+)?)$'),
                          self.str)

  def fill_properties_from_match(self):
    self.matches_format = True
    try:
      self.major = int(self.match.group('major'))
      self.minor = int(self.match.group('minor'))
      self.os = self.match.group('os_n')
      self.os_ver = int(self.match.group('os_v'))
    except TypeError:
      self.matches_format = False


class ImageVersion:
  """Information about dataproc image version"""

  def __init__(self, version_str):
    self.version = VersionParser(version_str)
    self.version.parse()

  def is_deprecated(self):
    if not self.version.matches_format:
      return False
    if self.version.major < 1:
      return True
    if self.version.major == 1 and self.version.minor < 4:
      return True
    if self.version.major == 1 and 4 <= self.version.minor <= 5:
      if self.version.os == 'debian' and self.os_ver < 10:
        return True
      if self.version.os == 'ubuntu' and self.os_ver < 18:
        return True
    return False


def prefetch_rule(context: models.Context):
  clusters_by_project[context.project_id] = dataproc.get_clusters(context)


def run_rule(context: models.Context,
             report: lint.LintReportRuleInterface) -> None:
  clusters = clusters_by_project[context.project_id]
  if not clusters:
    report.add_skipped(None, 'no dataproc clusters found')

  for cluster in clusters:
    if ImageVersion(cluster.image_version).is_deprecated():
      report.add_failed(cluster)
    else:
      report.add_ok(cluster)
