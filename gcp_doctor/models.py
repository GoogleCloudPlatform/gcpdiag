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
"""Data structures representing generic objects in GCP."""

import abc
import dataclasses
from typing import Iterable, List, Mapping, Optional

from gcp_doctor import utils


def _mapping_str(mapping: Mapping[str, str]) -> str:
  return ','.join(f'{k}={v}' for k, v in sorted(mapping.items()))


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # list of project ids (e.g.: 'my-project', 'anotherproject', etc.), mandatory
  projects: List[str]
  # list of GCP regions (e.g.: 'us-central1')
  regions: Optional[List[str]]
  # list of "label sets" that must match.
  labels: Optional[List[Mapping[str, str]]]

  # the selected resources are the intersection of projects, regions,
  # and labels(i.e. all must match), but each value in projects, regions, and
  # labels is a OR, so it means:
  # (project1 OR project2) AND
  # (region1 OR region2) AND
  # ({label1=value1,label2=value2} OR {label3=value3})

  def __init__(self,
               projects: Iterable[str],
               regions: Optional[Iterable[str]] = None,
               labels: Optional[Iterable[Mapping[str, str]]] = None):
    """Args:

      projects: projects that should be inspected.
      regions: only include resources in these GCP regions.
      labels: only include resources with these labels. Expected is a list
        (iterable) of dicts, where the dicts represent a set of label=value
        pairs that must match.

        Example: `[{'label1'='bla', 'label2'='baz'}, {'label1'='foo'}]`. This
        will
        match resources that either have label1=bla and label2=baz, or
        label1=foo.
    """

    self.projects = list(projects)
    if not self.projects:
      raise ValueError('projects must be a non-empty list')

    if regions:
      self.regions = list(regions)
      for region in self.regions:
        if not utils.is_region(region):
          raise ValueError(region + " doesn't look like a region")
    else:
      self.regions = None

    if labels:
      self.labels = []
      for l in labels:
        # pylint: disable=isinstance-second-argument-not-valid-type
        # (see: https://github.com/PyCQA/pylint/issues/3507)
        if not isinstance(l, Mapping):
          raise ValueError('labels must be Iterable[Mapping[str,str]]')
        self.labels.append(l)
    else:
      self.labels = None

  def __str__(self):
    string = 'projects: ' + ','.join(self.projects)
    if self.regions:
      string += ', regions: ' + ','.join(self.regions)
    if self.labels:
      string += ', labels: {' + '},{'.join(
          _mapping_str(label_set) for label_set in self.labels) + '}'
    return string

  def __hash__(self):
    return self.__str__().__hash__()

  def match_project_resource(self, location: Optional[str],
                             labels: Optional[Mapping[str, str]]) -> bool:
    """Return true if a resource in a project matches with this context."""

    # Match location.
    if self.regions:
      if not location:
        return False
      if not any(location.startswith(reg) for reg in self.regions):
        return False

    # Match labels.
    if self.labels:
      if not labels:
        return False
      for label_set in self.labels:
        if all(labels.get(k) == v for k, v in label_set.items()):
          break
      else:
        return False

    # Everything matched.
    return True


class Resource(abc.ABC):
  """Represents a single resource in GCP."""
  _project_id: str

  def __init__(self, project_id):
    self._project_id = project_id

  def __str__(self):
    return self.full_path

  def __hash__(self):
    return self.full_path.__hash__()

  def __eq__(self, other):
    if self.__class__ == other.__class__:
      return self.full_path == other.full_path
    else:
      return False

  @property
  def project_id(self) -> str:
    """Project id (not project number)."""
    return self._project_id

  @property
  @abc.abstractmethod
  def full_path(self) -> str:
    """Returns the full path of this resource.

    Example: 'projects/gcpd-gke-1-9b90/zones/europe-west4-a/clusters/gke1'
    """
    pass

  @property
  def short_path(self) -> str:
    """Returns the short name for this resource.

    Note that it isn't clear from this name what kind of resource it is.

    Example: 'gcpd-gke-1-9b90/gke1'
    """
    return self.full_path
