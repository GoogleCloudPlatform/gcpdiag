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
Populates a dictionary of product rules with the next consecutive number of a rule.

This script scans the 'gcpdiag/lint' directory for products and their associated rule files.
It parses rule file names to extract severity, year, and rule number information.
Then, it organizes rules by product, year, and severity, and determines the next
consecutive rule number for each severity within a year. Finally, it uses Cookiecutter
to generate new rule files based on this information.
"""

import sys
from os import path, scandir
from re import match
from typing import Dict, Set

from cookiecutter.main import cookiecutter

SCRIPT_DIR = path.dirname(path.abspath('./gcpdiag/gcpdiag'))
sys.path.append(path.dirname(SCRIPT_DIR))

# pylint: disable=wrong-import-position
from gcpdiag.product_list import get_product_list
from gcpdiag.rule_classes import get_rule_classes

# pylint: enable=wrong-import-position

# Initialize rule numbers dictionary
# {"product": {"year": {"severity": "rule_number"}}}
rule_numbers: Dict[str, Dict[int, Dict[str, str]]] = {}

# Scan lint directory for products
for product_dir in scandir('./gcpdiag/lint/'):
  if product_dir.is_dir() and not product_dir.name.startswith('__'):
    rule_numbers[product_dir.name] = {}

# Iterate over each product
for product, rule in rule_numbers.items():
  product_path = f'./gcpdiag/lint/{product}'
  # {"year": {"severity": {"001", "002", "..."}}}
  years: Dict[int, Dict[str, Set[int]]] = {}

  # Scan files within each product directory
  for file in scandir(product_path):
    if file.is_file():
      # Sample filenames:
      #   - warn_2022_003_firewall_rules_permission.py
      #   - bp_2021_001_cloudops_enabled.py
      m = match(r'([a-z]{2,4})_(\d{4})_(\d{3})_([^.]+)\.(py)', file.name)
      if m:
        severity = m.group(1).upper()
        year = int(m.group(2))
        rule_number = int(m.group(3))

        # Organize rules by year and severity
        years.setdefault(year, {}).setdefault(severity, set()).add(rule_number)

  # Update rule numbers dictionary
  for year, severities in years.items():
    for severity, rules in severities.items():
      next_rule_number = f'{max(rules) + 1:03d}'
      rule.setdefault(year, {})[severity] = next_rule_number

# Use cookiecutter with the generated rule numbers
cookiecutter('./cookiecutter-gcpdiag-rule',
             extra_context={
                 '__products': get_product_list(),
                 '__rule_classes': get_rule_classes(),
                 '__rule_numbers': rule_numbers,
                 'severity': list(get_rule_classes().keys()),
                 'product': list(get_product_list().keys())
             })
