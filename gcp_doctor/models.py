# Lint as: python3
"""Data structures representing generic objects in GCP."""

import dataclasses


@dataclasses.dataclass
class Context:
  """List of resource groups / scopes that should be analyzed."""
  # list of project ids (e.g.: 'my-project', 'anotherproject', etc.)
  project_list: list[str] = None
  # list of GCP zones (e.g.: 'us-central1-a')
  zones_list: list[str] = None
  # list of labels (e.g.: 'mylabel', etc.)
  labels_list: list[str] = None
  # the selected resources are the intersection of project_list, zones_list, and
  # labels_list (i.e. all must match)


@dataclasses.dataclass
class Resource:
  """Represents a single resource in GCP."""
  project_id: str
  resource_path: str
