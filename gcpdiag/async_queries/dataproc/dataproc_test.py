'Tests for gcpdiag.async_queries.dataproc.Dataproc'
import asyncio
import unittest
from typing import List

import yaml  # type: ignore

from gcpdiag.async_queries.dataproc import dataproc
from gcpdiag.async_queries.utils import fake_api


class FakeProjectRegions:

  def __init__(self, regions: List[str]) -> None:
    self.regions = regions

  async def get_all(self) -> List[str]:
    return self.regions


class TestProjectRegions(unittest.IsolatedAsyncioTestCase):
  'Tests for gcpdiag.async_queries.dataproc.Dataproc'

  def setUp(self) -> None:
    self.project_regions = FakeProjectRegions(
        regions=['westeros-central1', 'essos-east2'])
    self.westeros_list_call = fake_api.APICall(
        method='GET',
        url=('https://dataproc.googleapis.com/v1/projects/test-project/regions/'
             'westeros-central1/clusters'))
    self.essos_list_call = fake_api.APICall(
        'GET',
        'https://dataproc.googleapis.com/v1/projects/test-project/regions/essos-east2/clusters'
    )

    self.api = fake_api.FakeAPI(responses=[(self.westeros_list_call,
                                            yaml.safe_load("""
        clusters:
          - clusterName: westeros1
            status:
              state: RUNNING
          - clusterName: westeros2
            status:
              state: UNKNOWN
        """)),
                                           (self.essos_list_call,
                                            yaml.safe_load("""
        clusters:
          - clusterName: essos1
            status:
              state: RUNNING
        """))])
    self.dataproc = dataproc.Dataproc(api=self.api,
                                      project_id='test-project',
                                      project_regions=self.project_regions)

  async def test_list_clusters(self) -> None:
    clusters = await self.dataproc.list_clusters()
    self.assertListEqual(['westeros1', 'westeros2', 'essos1'], clusters)

  async def test_cluster_status(self) -> None:
    westeros1, westeros2, essos1 = await asyncio.gather(*[
        self.dataproc.get_cluster_by_name(n)
        for n in ['westeros1', 'westeros2', 'essos1']
    ])
    self.assertEqual('RUNNING', westeros1.status)
    self.assertEqual('UNKNOWN', westeros2.status)
    self.assertEqual('RUNNING', essos1.status)

  async def test_deduplication(self) -> None:
    await asyncio.gather(self.dataproc.get_cluster_by_name('westeros1'),
                         self.dataproc.get_cluster_by_name('westeros1'))
    self.assertEqual(1, self.api.count_calls(self.westeros_list_call))
