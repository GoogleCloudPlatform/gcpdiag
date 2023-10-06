""" Gateway for Dataproc service """
import asyncio
import functools
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol

from gcpdiag.async_queries.utils import loader, protocols
from gcpdiag.queries import dataproc


class Region:
  """ Helper class encapsulating Dataproc operations within a region """
  _api: protocols.API
  _project_id: str
  _region: str
  _data: Optional[Any]

  def __init__(self, api: protocols.API, project_id: str, region: str):
    self._api = api
    self._project_id = project_id
    self._region = region
    self._data = None

  async def load(self) -> None:
    assert self._data is None
    self._data = await self._api.call(
        method='GET',
        url=
        'https://dataproc.googleapis.com/v1/projects/{project_id}/regions/{region}/clusters'
        .format(project_id=self._project_id, region=self._region))

  @functools.cached_property
  def clusters(self) -> List[dataproc.Cluster]:
    return [self._mk_cluster(d) for d in self._clusters_descriptions]

  @property
  def _clusters_descriptions(self) -> List[Any]:
    assert isinstance(self._data, Mapping)
    descs = self._data.get('clusters', [])
    assert isinstance(descs, List)
    return descs

  def _mk_cluster(self, desc: Any) -> dataproc.Cluster:
    assert isinstance(desc, Mapping)
    assert 'clusterName' in desc
    assert isinstance(desc['clusterName'], str)
    return dataproc.Cluster(name=desc['clusterName'],
                            project_id=self._project_id,
                            resource_data=desc)


class ProjectRegions(Protocol):

  async def get_all(self) -> Iterable[str]:
    pass


class Dataproc:
  """ Gateway for Dataproc service """
  _api: protocols.API
  _project_id: str
  _project_regions: ProjectRegions
  _clusters_by_name: Dict[str, dataproc.Cluster]
  _loader: loader.Loader

  def __init__(self, api: protocols.API, project_id: str,
               project_regions: ProjectRegions) -> None:
    self._api = api
    self._project_id = project_id
    self._project_regions = project_regions
    self._clusters_by_name = {}
    self._loader = loader.Loader(self._load)

  async def list_clusters(self) -> List[str]:
    await self._loader.ensure_loaded()
    return list(self._clusters_by_name.keys())

  async def get_cluster_by_name(self, cluster_name: str) -> dataproc.Cluster:
    await self._loader.ensure_loaded()
    return self._clusters_by_name[cluster_name]

  async def _load(self) -> None:
    regions_names = await self._project_regions.get_all()
    regions = [self._mk_region(r) for r in regions_names]
    await asyncio.gather(*[r.load() for r in regions])
    for r in regions:
      for cluster in r.clusters:
        self._clusters_by_name[cluster.name] = cluster

  def _mk_region(self, region: str) -> Region:
    return Region(api=self._api, project_id=self._project_id, region=region)
