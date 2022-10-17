'Tests for gcpdiag.async_queries.ProjectRegions'
from asyncio import gather
from unittest import IsolatedAsyncioTestCase

from gcpdiag.async_queries.utils import fake_api

from .project_regions import ProjectRegions


class TestProjectRegions(IsolatedAsyncioTestCase):
  'Tests for gcpdiag.async_queries.ProjectRegions'

  def setUp(self) -> None:
    self.call = fake_api.APICall(
        'GET',
        'https://compute.googleapis.com/compute/v1/projects/test-project/regions',
        None)
    self.api = fake_api.FakeAPI(responses=[(self.call, {
        'items': [{
            'name': 'westeros-central1'
        }, {
            'name': 'essos-east2'
        }]
    })])
    self.project_regions = ProjectRegions(api=self.api,
                                          project_id='test-project')

  async def test_happy_path(self) -> None:
    result = await self.project_regions.get_all()
    self.assertListEqual(['westeros-central1', 'essos-east2'], result)

  async def test_deduplication(self) -> None:
    await gather(self.project_regions.get_all(), self.project_regions.get_all())
    self.assertEqual(self.api.count_calls(self.call), 1)
