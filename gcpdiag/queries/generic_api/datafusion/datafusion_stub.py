"""Stub for Data Fusion API."""

from gcpdiag.queries.generic_api.api_build.generic_api_stub import \
    GenericApiStub


class DataFusionApiStub(GenericApiStub):
  """Stub for Data Fusion API."""

  def __init__(self):
    super().__init__('datafusion1')

  def get_system_profiles(self):
    return self._load_json('datafusion-system-compute-profile')

  def get_all_namespaces(self):
    return self._load_json('namespaces')

  def get_user_profiles(self, namespace: str):
    return self._load_json(f'datafusion-{namespace}-user-compute-profile')
