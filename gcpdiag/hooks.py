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
"""Hooks function definitions.

Hooks are functions that are called in different parts of the code base,
and used to execute some functionality that might be only required in
certain environments.
"""


def set_lint_args_hook(args):
  """Called after lint command arguments were parsed."""
  try:
    # This is for Google-internal use only and allows us to modify
    # default options for internal use.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks as google_internal
    google_internal.set_lint_args_hook(args)
  except ImportError:
    pass


def set_runbook_args_hook(args):
  """Called after runbook command arguments were parsed."""
  try:
    # This is for Google-internal use only and allows us to modify
    # default options for internal use.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks as google_internal
    google_internal.set_runbook_args_hook(args)
  except ImportError:
    pass


def verify_access_hook(project_id: str):
  """Called to do additional authorization verifications."""
  try:
    # gcpdiag_google_internal contains code that we run only internally
    # at Google, so this import will fail in the public version.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks as google_internal
    google_internal.verify_access_hook(project_id)
  except ImportError:
    pass


def request_builder_hook(*args, **kwargs):
  """Called when creating HTTP requests."""
  try:
    # This is for Google-internal use only and allows us to modify the request
    # to make it work also internally. The import will fail for the public
    # version of gcpdiag.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks
    hooks.request_builder_hook(*args, **kwargs)
  except ImportError:
    pass


def post_lint_hook(report):
  """Called after lint command has run."""
  try:
    # gcpdiag_google_internal contains code that we run only internally
    # at Google, so this import will fail in the public version.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks as google_internal
    google_internal.post_lint_hook(report)
  except ImportError:
    pass


def post_runbook_hook(report):
  """Called after runbook command has run."""
  try:
    # gcpdiag_google_internal contains code that we run only internally
    # at Google, so this import will fail in the public version.
    # pylint: disable=import-outside-toplevel
    from gcpdiag_google_internal import hooks as google_internal
    google_internal.post_runbook_hook(report)
  except ImportError:
    pass
