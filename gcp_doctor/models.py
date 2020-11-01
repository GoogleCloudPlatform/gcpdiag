# Lint as: python3
"""Data structures representing generic objects in GCP."""

import abc
from typing import List

import dataclasses


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # list of project ids (e.g.: 'my-project', 'anotherproject', etc.)
  project_list: List[str] = None
  # list of GCP zones (e.g.: 'us-central1-a')
  zones_list: List[str] = None
  # list of labels (e.g.: 'mylabel', etc.)
  labels_list: List[str] = None
  # the selected resources are the intersection of project_list, zones_list, and
  # labels_list (i.e. all must match)


@dataclasses.dataclass
class Resource(abc.ABC):
  """Represents a single resource in GCP."""
  project_id: str

  @abc.abstractmethod
  def get_full_path(self):
    pass

