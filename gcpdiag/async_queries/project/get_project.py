""" Helper method to initialize Project object """
from gcpdiag.async_queries import api, creds
from gcpdiag.async_queries.project import project

_creds = creds.GcpdiagCreds()
_api = api.API(creds=_creds)


def get_project(project_id: str) -> project.Project:
  return project.Project(project_id=project_id, api=_api)
