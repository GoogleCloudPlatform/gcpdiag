# Copyright 2022 Google LLC
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
"""Builds don't fail because of failed registry permissions.

Builds configured to upload image to Artifact Registry must use service account  that has write
permission for it.
"""
import dataclasses
import re
from typing import Iterable, Tuple

from gcpdiag import lint, models
from gcpdiag.queries import artifact_registry, crm, gcb, iam

PERMISSION = 'artifactregistry.repositories.uploadArtifacts'


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  builds = gcb.get_builds(context)
  if len(builds) == 0:
    report.add_skipped(None, 'no recent builds')
    return
  project = crm.get_project(context.project_id)
  found = list(
      find_builds_without_image_upload_permission(
          builds.values(),
          default_sa=f'{project.number}@cloudbuild.gserviceaccount.com',
      ))
  if len(found) == 0:
    report.add_ok(project)
  for status in found:
    report.add_failed(
        status.build,
        reason=f'{status.service_account} can not '
        f'read {status.artifact_repository} registry in '
        f'{status.artifact_location} in {status.artifact_project} project.',
    )


@dataclasses.dataclass
class FailedBuildStatus:
  build: gcb.Build
  service_account: str
  artifact_project: str
  artifact_location: str
  artifact_repository: str


def find_builds_without_image_upload_permission(
    builds: Iterable[gcb.Build],
    default_sa: str,
) -> Iterable[FailedBuildStatus]:
  for build in builds:
    sa = (build.service_account or default_sa).split('/')[-1]
    if build.status != 'FAILURE':
      continue
    for project, location, repository in get_used_registries(build.images):
      if not can_read_registry(sa, project, location, repository):
        yield FailedBuildStatus(build, sa, project, location, repository)


def get_used_registries(
    images: Iterable[str]) -> Iterable[Tuple[str, str, str]]:
  result = set()
  for image in images:
    m = re.match('([^.]+)-docker.pkg.dev/([^/]+)/([^/]+)/([^.]+)', image)
    if m:
      project = m.group(2)
      location = m.group(1)
      repository = m.group(3)
      result.add((project, location, repository))
  return result


def can_read_registry(service_account_email: str, project_id: str,
                      location: str, repository: str):
  project_policy = iam.get_project_policy(project_id)
  member = f'serviceAccount:{service_account_email}'
  if project_policy.has_permission(member, PERMISSION):
    return True
  registry_policy = artifact_registry.get_registry_iam_policy(
      project_id, location, repository)
  registry_policy.has_permission(member, PERMISSION)
  return registry_policy.has_permission(member, PERMISSION)
