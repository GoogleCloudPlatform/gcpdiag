# Lint as: python3
"""Data structures representing generic objects in GCP."""

import abc
import dataclasses
from typing import Iterable, List, Mapping, Optional

from gcp_doctor import utils


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # list of project ids (e.g.: 'my-project', 'anotherproject', etc.), mandatory
  projects: List[str]
  # list of GCP regions (e.g.: 'us-central1')
  regions: Optional[List[str]]
  # map of labels (e.g.: 'mylabel', etc.)
  labels: Optional[Mapping[str, str]]

  # the selected resources are the intersection of projects, regions,
  # and labels(i.e. all must match), but each value in projects, regions, and
  # labels is a OR, so it means:
  # (project1 OR project2) AND (region1 OR region2) AND (label1=value1 OR label2=value2)

  def __init__(self,
               projects: Iterable[str],
               regions: Optional[Iterable[str]] = None,
               labels: Optional[Mapping[str, str]] = None):
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
      self.labels = dict(labels)
    else:
      self.labels = None

  def __str__(self):
    string = 'projects: ' + ','.join(self.projects)
    if self.regions:
      string += ', regions: ' + ','.join(self.regions)
    if self.labels:
      string += ', labels: ' + ','.join(
          label + '=' + self.labels[label] for label in self.labels.keys())
    return string

  def match_project_resource(self, location: Optional[str],
                             labels: Optional[Mapping[str, str]]) -> bool:
    """Return true if a resource in a project matches with this context."""
    # match location
    if self.regions:
      if not location:
        return False
      if not any(location.startswith(reg) for reg in self.regions):
        return False
    # match labels
    if self.labels:
      if not labels:
        return False
      for label in self.labels.keys():
        # does any of the context labels match?
        if label in labels.keys() and labels[label] == self.labels[label]:
          return True
      return False
    return True


class Resource(abc.ABC):
  """Represents a single resource in GCP."""
  _project_id: str

  def __init__(self, project_id):
    self._project_id = project_id

  def __str__(self):
    return self.get_full_path()

  @property
  def project_id(self) -> str:
    return self._project_id

  @abc.abstractmethod
  def get_full_path(self):
    pass

  def get_short_path(self) -> str:
    return self.get_full_path()
