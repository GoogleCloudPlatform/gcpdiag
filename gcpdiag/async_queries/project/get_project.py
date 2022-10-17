""" Helper method to initialize Project object """
from gcpdiag.async_queries.api import get_api
from gcpdiag.async_queries.project import project

_api = get_api.get_api()


def get_project(project_id: str) -> project.Project:
  return project.Project(project_id=project_id, api=_api)
