""" Class representing different services available within a GCP project """
import functools

from gcpdiag.async_queries import project_regions
from gcpdiag.async_queries.dataproc import dataproc
from gcpdiag.async_queries.utils import protocols


class Project:
  """ Class representing different services available within a GCP project """
  _project_id: str
  _api: protocols.API

  def __init__(self, api: protocols.API, project_id: str) -> None:
    self._project_id = project_id
    self._api = api

  @functools.cached_property
  def dataproc(self) -> dataproc.Dataproc:
    return dataproc.Dataproc(api=self._api,
                             project_id=self._project_id,
                             project_regions=self._project_regions)

  @functools.cached_property
  def _project_regions(self) -> project_regions.ProjectRegions:
    return project_regions.ProjectRegions(project_id=self._project_id,
                                          api=self._api)
