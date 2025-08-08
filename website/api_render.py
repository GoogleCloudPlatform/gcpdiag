#!/usr/bin/env python3

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

# pylint: disable=cyclic-import
"""Generates API documentation for queries modules"""
import textwrap
from pathlib import Path

import pdoc

pwd = Path().parent
modules = pwd / '..' / 'gcpdiag'
output = pwd / 'content' / 'en' / 'docs' / 'development' / 'api'

pdoc.render.configure(template_directory=pwd / 'assets' / 'pdoc_templates',
                      docformat='google')


def customize_index_file(file_directory, page_title, page_link_title,
                         page_weight, page_description) -> None:
  """pdoc creates an index.html file per directory, however Hugo expects _index.html file.
    This method removes the default index.html file and creates a custom one per directory

  Args:
      file_directory (pathlib.PosixPath): Path to parent directory containing index.html file.
      page_tile (str): Title for the index page.
      page_link_title (str): Used for creating a link to the index page.
      page_weight (int): Used for ordering the index page in lists.
      page_description (str):

  """
  filename = file_directory / 'index.html'
  # For backward compartibility with 3.7 without missing_ok flag
  try:
    filename.unlink()
  except FileNotFoundError:
    pass

  new_filename = file_directory / '_index.html'

  try:
    new_filename.unlink()
  except FileNotFoundError:
    pass

  new_filename.write_text(
      textwrap.dedent(f'''
    ---
    title: {page_title}
    linkTitle: {page_link_title}
    weight: {page_weight}
    description: >
      {page_description}
    ---
    '''))


# Generate API documentation for queries module
queries_output = output / 'queries'
queries = modules / 'queries'
query_modules = []

for module in queries.iterdir():
  if (module.suffix == '.py' and 'test' not in module.name and
      'stub' not in module.name and '__init__' not in module.name):
    query_modules.append(module)

# Create output directory if it does not exist
if not queries_output.exists():
  queries_output.mkdir(parents=True)

pdoc.pdoc(*query_modules, output_directory=queries_output)

# Generate API documentation for models module
models_output = output / 'models'
models = modules / 'models.py'

# Create output directory if it does not exist
if not models_output.exists():
  models_output.mkdir(parents=True)

pdoc.pdoc(models, output_directory=models_output)

# Customize api index.html
title = 'API Documentation'
link_title = 'API'
weight = 100
description = 'Documentation for reusable libraries'
customize_index_file(output, title, link_title, weight, description)

# Customize queries index.html
title = 'Queries module'
link_title = 'Queries'
weight = 100
description = 'Documentation for queries module'
customize_index_file(queries_output, title, link_title, weight, description)

# Customize models index.html
title = 'Models module'
link_title = 'Models'
weight = 100
description = 'Documentation for models module'
customize_index_file(models_output, title, link_title, weight, description)
