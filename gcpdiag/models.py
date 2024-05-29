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
import re
from types import MappingProxyType
from typing import Any, Generic, Iterable, List, Mapping, Optional, TypeVar

from gcpdiag import utils


def _mapping_str(mapping: Mapping[str, str]) -> str:
  return ','.join(f'{k}={v}' for k, v in sorted(mapping.items()))


class Messages(dict):

  def get_msg(self, template: str, **kwargs):
    return self.get(
        template,
        'NOTICE: No message available to parse for this step').format(**kwargs)


T = TypeVar('T')
V = TypeVar('V', bound=Any)


class Parameter(dict[T, V], Generic[T, V]):
  """Class to store parameters"""

  def __init__(self, *args, **kwargs):
    super().__init__()
    for dict_arg in args:
      for key, value in dict_arg.items():
        self[key] = value
    for key, value in kwargs.items():
      self[key] = value

  def _parse_value(self, value: str) -> Any:
    """Make all values lower string and strip whitespaces."""
    if isinstance(value, str):
      return value.strip().lower()
    return value

  def __setitem__(self, key: T, value: V) -> None:
    super().__setitem__(key, self._parse_value(value))

  def update(self, *args, **kwargs) -> None:
    for k, v in dict(*args, **kwargs).items():
      self[k] = v

  def setdefault(self, key: T, default: V = None) -> V:
    if key not in self:
      converted_default = self._parse_value(default) if isinstance(
          default, str) else default
      self[key] = converted_default
    return super().setdefault(key, self[key])


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # project_id of project that is being analyzed, mandatory
  project_id: str
  # a pattern of sub project resources that match
  resources_pattern: Optional[re.Pattern]
  # list of GCP all locations to use as linting scope
  # i.e. regions (e.g.: 'us-central1') or zone (e.g.: 'us-central1-a').
  # a compiled project resources provided by user
  locations_pattern: Optional[re.Pattern]

  # list of "label sets" that must match.
  labels: Optional[Mapping[str, str]]
  # list of "runbook parameters sets" that must match.
  parameters: Parameter[str, Any]

  # the selected resources are the intersection of project_id, locations,
  # and labels(i.e. all must match), but each value in locations, and
  # labels is a OR, so it means:
  # project_id AND
  # (region1 OR region2) AND
  # ({label1=value1,label2=value2} OR {label3=value3})

  def __init__(self,
               project_id: str,
               locations: Optional[Iterable[str]] = None,
               labels: Optional[Mapping[str, str]] = None,
               parameters: Optional[Parameter[str, str]] = None,
               resources: Optional[Iterable[str]] = None):
    """Args:

      project: project_id of project that should be inspected.
      locations: only include resources in these GCP locations.
      labels: only include resources with these labels. Expected
        is a dict, is a set of key=value pairs that must match.

        Example: `{'key1'='bla', 'key2'='baz'}`. This
        will match resources that either have key1=bla or key2=baz.
      resources: only include sub project resources with this name attribute.
    """

    self.project_id = project_id

    if locations:
      if not isinstance(locations, List):
        raise ValueError(
            str(locations) + ' did not supply full list of locations')
      for location in locations:
        if not (utils.is_region(location) or utils.is_zone(location)):
          raise ValueError(location + ' does not look like a valid region/zone')

      self.locations_pattern = re.compile('|'.join(locations), re.IGNORECASE)
    else:
      self.locations_pattern = None

    if labels:
      if not isinstance(labels, Mapping):
        raise ValueError('labels must be Mapping[str,str]]')

      self.labels = labels
    else:
      self.labels = None

    if resources:
      if not isinstance(resources, List):
        raise ValueError(
            str(resources) + ' did not supply full list of resources')

      self.resources_pattern = re.compile('|'.join(resources), re.IGNORECASE)

    else:
      self.resources_pattern = None

    if parameters:
      if not isinstance(parameters, Mapping):
        raise ValueError('parameters must be Mapping[str,str]]')

      self.parameters = Parameter(parameters)
    else:
      self.parameters = Parameter()
    self.parameters['project_id'] = self.project_id

  def __str__(self):
    string = 'project: ' + self.project_id
    if self.resources_pattern:
      string += ', resources: ' + self.resources_pattern.pattern
    if self.locations_pattern:
      string += ', locations (regions/zones): ' + self.locations_pattern.pattern
    if self.labels:
      string += ', labels: {' + _mapping_str(self.labels) + '}'
    if self.parameters:
      string += ', parameters: {' + _mapping_str(self.parameters) + '}'
    return string

  def __hash__(self):
    return self.__str__().__hash__()

  IGNORELOCATION = 'IGNORELOCATION'
  IGNORELABEL = MappingProxyType({'IGNORELABEL': 'IGNORELABEL'})

  def match_project_resource(
      self,
      resource: Optional[str],
      location: Optional[str] = IGNORELOCATION,
      labels: Optional[Mapping[str, str]] = IGNORELABEL,
  ) -> bool:
    """Compare resource fields to the name and/or location and/or labels supplied
    by the user and return a boolean outcome depending on the context.

    Args:
      resource: name of the resource under analysis. Always inspected if user
      supplied a name criteria

      location: region or zone of the resource. IGNORELOCATION completely skips analysis
      of the location even if user has supplied location criteria

      labels: labels in the resource under inspection. Functions which do not
      support labels can completely skip checks by providing the IGNORELABEL constant

    Returns:
      A boolean which indicates the outcome of the analysis
    """

    # Match resources.
    if self.resources_pattern:
      if not resource or not self.resources_pattern.match(resource):
        return False

    # Match location.
    if self.locations_pattern and location is not self.IGNORELOCATION:
      if not location or not self.locations_pattern.match(location):
        return False

    # Match labels.
    if self.labels and labels is not self.IGNORELABEL:
      if not labels:
        return False

      if any(labels.get(k) == v for k, v in self.labels.items()):
        pass
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

  def __lt__(self, other):
    return self.full_path < other.full_path

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

    Example: 'projects/gcpdiag-gke-1-9b90/zones/europe-west4-a/clusters/gke1'
    """
    pass

  @property
  def short_path(self) -> str:
    """Returns the short name for this resource.

    Note that it isn't clear from this name what kind of resource it is.

    Example: 'gke1'
    """
    return self.full_path
