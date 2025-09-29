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
import abc
import dataclasses
import re
from typing import Iterable, Set

from gcpdiag import lint, models
from gcpdiag.queries import artifact_registry, crm, gcb, iam

PERMISSION = 'artifactregistry.repositories.uploadArtifacts'
GCR_LOCATION_MAP = {
    'gcr.io': 'us',
    'asia.gcr.io': 'asia',
    'eu.gcr.io': 'europe',
    'us.gcr.io': 'us',
}


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  builds = gcb.get_builds(context)
  if len(builds) == 0:
    report.add_skipped(None, 'no recent builds')
    return
  project = crm.get_project(context.project_id)
  found = list(
      find_builds_without_image_upload_permission(
          context,
          builds.values(),
          default_sa=f'{project.number}@cloudbuild.gserviceaccount.com',
      ))
  if len(found) == 0:
    report.add_ok(project)
  for status in found:
    report.add_failed(
        status.build,
        reason=f'{status.service_account} can not '
        f'read {status.repository.format_message()}',
    )


@dataclasses.dataclass
class FailedBuildStatus:
  build: gcb.Build
  service_account: str
  repository: 'Repository'


class Repository(abc.ABC):

  @abc.abstractmethod
  def can_read_registry(self, context: models.Context,
                        service_account_email: str) -> bool:
    pass

  @abc.abstractmethod
  def format_message(self) -> str:
    pass


class GcrRepository(Repository):
  """Represents AR or GCR docker repository that can be accessed by gcr.io domain."""

  def __init__(self, project_id: str, repository: str):
    self.project_id = project_id
    self.repository = repository

  def can_read_registry(self, context: models.Context,
                        service_account_email: str) -> bool:
    if not artifact_registry.get_project_settings(
        self.project_id).legacy_redirect:
      # In case of failure to upload to gcr.io cloud build provides useful information.
      return True
    location = GCR_LOCATION_MAP[self.repository]
    return ArtifactRepository(self.project_id, location, self.repository) \
        .can_read_registry(context, service_account_email)

  def format_message(self) -> str:
    return f'{self.repository} registry in {self.project_id} project.'


class ArtifactRepository(Repository):
  """Represents AR docker repository that can be accessed by pkg.dev domain."""

  def __init__(self, project_id: str, location: str, repository: str):
    self.project_id = project_id
    self.location = location
    self.repository = repository

  def can_read_registry(self, context: models.Context,
                        service_account_email: str) -> bool:
    project_policy = iam.get_project_policy(context)
    member = f'serviceAccount:{service_account_email}'
    if project_policy.has_permission(member, PERMISSION):
      return True
    registry_policy = artifact_registry.get_registry_iam_policy(
        context, self.location, self.repository)
    return registry_policy.has_permission(member, PERMISSION)

  def format_message(self) -> str:
    return (f'{self.repository} registry in {self.location} in'
            f' {self.project_id} project.')


def find_builds_without_image_upload_permission(
    context: models.Context,
    builds: Iterable[gcb.Build],
    default_sa: str,
) -> Iterable[FailedBuildStatus]:
  for build in builds:
    sa = (build.service_account or default_sa).split('/')[-1]
    if build.status != 'FAILURE':
      continue
    for repository in get_used_registries(build.images):
      if not repository.can_read_registry(context, sa):
        yield FailedBuildStatus(build, sa, repository)


def get_used_registries(images: Iterable[str]) -> Iterable[Repository]:
  result: Set[Repository] = set()
  for image in images:
    m = re.match('([^.]+)-docker.pkg.dev/([^/]+)/([^/]+)/(?:[^.]+)', image)
    if m:
      result.add(
          ArtifactRepository(
              project_id=m.group(2),
              location=m.group(1),
              repository=m.group(3),
          ))
    m = re.match('((?:[^.]+-)?gcr.io)/([^/]+)/(?:[^.]+)', image)
    if m:
      result.add(GcrRepository(
          project_id=m.group(2),
          repository=m.group(1),
      ))
  return result
