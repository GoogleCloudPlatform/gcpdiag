""" Gateway for extracting available GCP regions """
from typing import Any, Iterable, List, Mapping, Optional

from gcpdiag.async_queries.utils import loader, protocols


class ProjectRegions:
  """ Gateway for extracting available GCP regions """
  api: protocols.API
  project_id: str
  loader: loader.Loader
  regions: Optional[List[str]]

  def __init__(self, api: protocols.API, project_id: str) -> None:
    self.api = api
    self.project_id = project_id
    self.loader = loader.Loader(self.load)
    self.regions = None

  async def get_all(self) -> List[str]:
    await self.loader.ensure_loaded()
    assert self.regions is not None
    return self.regions

  async def load(self) -> None:
    resp = await self.call_api()
    self.regions = self.parse_resp(resp)

  async def call_api(self) -> Any:
    return await self.api.call(
        method='GET',
        url=
        'https://compute.googleapis.com/compute/v1/projects/{project_id}/regions'
        .format(project_id=self.project_id))

  def parse_resp(self, resp: Any) -> List[str]:
    assert isinstance(resp, Mapping)
    assert 'items' in resp
    assert isinstance(resp['items'], Iterable)
    return [r['name'] for r in resp.get('items', [])]
