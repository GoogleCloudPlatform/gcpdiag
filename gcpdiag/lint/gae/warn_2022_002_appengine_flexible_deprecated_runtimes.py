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
"""App Engine Flexible versions don't use deprecated runtimes.

The following runtimes are deprecated: 'go16', 'go18', 'python27'.
"""

from gcpdiag import lint, models
from gcpdiag.queries import gae

DEPRECATED_RUNTIMES = ['go16', 'go18', 'python27']


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  versions = gae.get_versions(context)
  if not versions:
    report.add_skipped(None, 'no versions found for flexible environment')
    return

  for version in sorted(versions.values(), key=lambda version: version.id):
    if version.env != 'flexible':
      report.add_skipped(None, 'no versions found for flexible environment')
      return
    if version.runtime in DEPRECATED_RUNTIMES:
      report.add_failed(
          version, f'the version \'{version.id}\' for '
          f'the service \'{version.service.name}\' '
          f'uses deprecated runtime {version.runtime}')
    else:
      report.add_ok(version)
