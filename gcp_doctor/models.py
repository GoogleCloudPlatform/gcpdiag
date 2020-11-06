# Lint as: python3
"""Data structures representing generic objects in GCP."""

import dataclasses
from typing import Iterable, List, Optional

from gcp_doctor import utils


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # list of project ids (e.g.: 'my-project', 'anotherproject', etc.), mandatory
  project_list: List[str]
  # list of GCP regions (e.g.: 'us-central1')
  regions_list: Optional[List[str]]
  # list of labels (e.g.: 'mylabel', etc.)
  labels_list: Optional[List[str]]

  # the selected resources are the intersection of project_list, regions_list,
  # and labels_list (i.e. all must match)

  def __init__(self,
               project_list: Iterable[str],
               regions_list: Optional[Iterable[str]] = None,
               labels_list: Optional[Iterable[str]] = None):
    self.project_list = list(project_list)
    if not self.project_list:
      raise ValueError('project_list must be a non-empty list')

    if regions_list:
      self.regions_list = list(regions_list)
      for region in self.regions_list:
        if not utils.is_region(region):
          raise ValueError(region + " doesn't look like a region")
    else:
      self.regions_list = None

    if labels_list:
      self.labels_list = list(labels_list)
    else:
      self.labels_list = None

  def __str__(self):
    string = 'projects: ' + ','.join(self.project_list)
    if self.regions_list:
      string += ', regions: ' + ','.join(self.regions_list)
    if self.labels_list:
      string += ', labels: ' + ','.join(self.labels_list)
    return string


# note: this should be an abstract class, but it doesn't work with mypi
# due to this bug: https://github.com/python/mypy/issues/5374
@dataclasses.dataclass
class Resource:
  """Represents a single resource in GCP."""
  project_id: str

  def get_full_path(self):
    return f'project/{self.project_id}/UNKNOWN'

  def get_short_path(self) -> str:
    return self.get_full_path()
