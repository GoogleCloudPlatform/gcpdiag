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
"""
Places generated lint rule files under their target directories

This cookiecutter hook moves the generated files to thir respective directories
and removes a temporary directory.
"""
import os
import pathlib
import shutil

source_dir = '.'
target_dir = '..'

content = os.walk(source_dir)

for root, dirs, files in content:
  if files:
    # move pre-populated files to their target directories
    for file in files:
      pathlib.Path(os.path.dirname(os.path.join(target_dir, root,
                                                file))).mkdir(parents=True,
                                                              exist_ok=True)
      os.rename(os.path.join(root, file), os.path.join(target_dir, root, file))

# delete the temporary cookiecutter directory
shutil.rmtree(os.path.join(target_dir, '{{ cookiecutter.__name }}'))
