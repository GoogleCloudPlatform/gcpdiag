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
"""pyinstaller configuration for gcpdiag.runbook."""

from PyInstaller.utils.hooks import collect_submodules

# update also bin/precommit-required-files
# note: keep in sync with modules in bin/runbook-starter-code-generator
hiddenimports = \
  collect_submodules('gcpdiag.runbook.crm') + \
  collect_submodules('gcpdiag.runbook.monitoring') + \
  collect_submodules('gcpdiag.runbook.gcp') + \
  collect_submodules('gcpdiag.runbook.iam') + \
  collect_submodules('gcpdiag.runbook.gke') + \
  collect_submodules('gcpdiag.runbook.gce') + \
  collect_submodules('gcpdiag.runbook.gce.util')
