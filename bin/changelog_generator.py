#!/usr/bin/env python3

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
"""Changelog Generator"""

import ast
import os
import re
import subprocess
import sys


def lint_name_generator(file_path):
  """Lint name regex generator"""
  parts = file_path.split('/')
  if len(parts) >= 4:
    group3 = parts[3]
    prefix = ''.join(c for c in group3 if c.isalpha() or c == '_').split(
        '__', maxsplit=1)[0]
    numbers = ''.join(
        c for c in group3 if c.isdigit() or c == '_').strip('_').split(
            '__', maxsplit=1)[0]
    return f"{parts[2]}/{prefix}/{numbers.rstrip('_')}"


def find_queries(file, commit):
  """find new queries and respective docstring"""
  if os.path.exists(file):
    with open(file, encoding='utf-8') as f:
      tree = ast.parse(f.read())
    f.close()
    content_changed = subprocess.check_output(
        ['git', 'show', '-p', f'{commit}',
         f'{file}']).decode('utf-8').split('\n')
    i = 0
    for item in content_changed:
      i = i + 1
      if item.startswith('+def '):
        file = file.split('/')[-1].split('.py')[0]
        match = re.search(r'def\s+(.+?)\(', item)
        function_name = ''
        if match:
          function_name = match.group(1)
          message = ''
          for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
              message = ast.get_docstring(node) or 'No Message found'

          final = file + '.' + function_name + ': ' + ' '.join(message.split())
          if final:
            return final
          else:
            return file + ': No function implemented'
  else:
    return file + ': No file found'


def generate_release_notes(old_commit, new_commit, current_version):
  """Generates release notes for version change"""

  commits = subprocess.check_output([
      'git', 'log', '--pretty=format:"%h %s"', '--no-merges',
      f'{old_commit}..{new_commit}'
  ]).decode('utf-8').split('\n')

  commits_dict = {}
  for commit in commits:
    if commit.strip():
      commit_id, commit_msg = commit.strip('"').split(' ', 1)
      commits_dict[commit_id] = commit_msg

  fixes = []
  new_runbooks = []
  new_lints = []
  new_queries = []

  for commit_item in commits_dict.items():
    commit = commit_item[0]
    commit_msg = commit_item[1]
    if commit_msg.startswith('Bump version:'):
      pass
    else:
      try:
        # Get the files changed in this commit
        files_changed = subprocess.check_output(
            ['git', 'show', '--name-status', '--pretty=format:""',
             f'{commit}']).decode('utf-8').split('\n')
        if len(files_changed) > 2:
          files_changed_dict = {}
          for file_info in files_changed:
            if file_info.strip():
              match = re.match(r'([AM])\t(.*)', file_info.strip('"'))
              if match:
                status, filename = match.groups()
                files_changed_dict[filename] = status

          all_files_existed = []
          all_new_files = []
          # Check if all changed files existed before this commit
          for file in files_changed_dict.items():
            if file[1] in ['M', 'T']:
              all_files_existed.append(file[0])
            elif file[1] == 'A':
              all_new_files.append(file[0])

          ignored_files = [
              'utils.py', 'generalized_steps.py', '__init__.py', 'constants.py',
              'flags.py', 'utils_test.py'
          ]

          if all_files_existed and not all_new_files:
            fixes.append(commit_msg)
          else:
            new_runbooks.extend([
                (re.sub(r'gcpdiag/runbook/|_|\.py', '-', f).strip('-') + ': ' +
                 commit_msg)
                for f in all_new_files
                if f.startswith('gcpdiag/runbook/') and f.endswith('.py') and
                f.split('/')[-1] not in ignored_files and
                not f.endswith('_test.py')
            ])
            new_lints.extend([
                (lint_name_generator(f) + ': ' + commit_msg)
                for f in all_new_files
                if f.startswith('gcpdiag/lint/') and f.endswith('.py') and
                f.split('/')[-1] not in ignored_files and
                not f.endswith('_test.py')
            ])
          all_files = all_files_existed + all_new_files
          new_queries.extend([
              find_queries(f, commit)
              for f in all_files
              if f.startswith('gcpdiag/queries/') and f.endswith('.py') and
              f.split('/')[-1] not in ignored_files and
              not f.endswith('_test.py') and not f.endswith('_stub.py')
          ])

      except subprocess.CalledProcessError:
        pass

  new_runbooks = list(dict.fromkeys(new_runbooks))
  new_lints = list(dict.fromkeys(new_lints))
  new_queries = list(dict.fromkeys(new_queries))
  new_queries = list(filter(None, new_queries))

  new_runbooks = [item.replace('_', r'\_') for item in new_runbooks]
  new_lints = [item.replace('_', r'\_') for item in new_lints]
  new_queries = [item.replace('_', r'\_') for item in new_queries]

  # Format release notes
  release_notes = f'\n\n# Release Notes for v{current_version}\n\n'  # Removed tag from title
  if new_lints:
    release_notes += '## New Lints\n\n' + '\n'.join(new_lints) + '\n\n'
  if new_runbooks:
    release_notes += '## New Runbooks\n\n' + '\n'.join(new_runbooks) + '\n\n'
  if new_queries:
    release_notes += '## New Queries\n\n' + '\n'.join(new_queries) + '\n\n'
  if fixes:
    release_notes += '## Fixes\n\n' + '\n'.join(fixes) + '\n\n'
  return release_notes


if __name__ == '__main__':

  with open('gcpdiag/config.py', encoding='utf-8') as fcg:
    for line in fcg:
      if line.startswith('VERSION ='):
        match_var = re.match(r"VERSION = '([\d.]+)", line)
        if match_var:
          current_ver = match_var.group(1)
          previous_version = f'v{float(current_ver) - 0.01}'
        else:
          print('Current version information is missing from gcpdiag/config.py')
          current_ver = input(
              'Please enter the current version e.g 0.77 or 0.76: ')
          if current_ver and re.match(r'^\d+\.\d{2}$', current_ver):
            previous_version = f'v{float(current_ver) - 0.01}'
            break
          else:
            print('No Current Version information found, exiting!!')
            sys.exit(1)

  fcg.close()
  #old_commit_id = "0fc34e64"
  #old_commit_id = 'v0.73'
  old_commit_id = previous_version
  new_commit_id = 'HEAD'
  release_notes_final = generate_release_notes(old_commit_id, new_commit_id,
                                               current_ver)
  print(release_notes_final)
