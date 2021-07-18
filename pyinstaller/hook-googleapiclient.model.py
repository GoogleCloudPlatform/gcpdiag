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
"""pyinstaller configuration for googleapiclient."""

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

# googleapiclient.model queries the library version via
# pkg_resources.get_distribution("google-api-python-client").version,
# so we need to collect that package's metadata
datas = copy_metadata('google_api_python_client')
datas += collect_data_files('googleapiclient.discovery',
                            excludes=['*.txt', '**/__pycache__'])
