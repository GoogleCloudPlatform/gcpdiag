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

  def get_system_preferences(self):
    return self._load_json('datafusion-system-preferences')

  def get_namespace_preferences(self, namespace: str):
    return self._load_json(f'datafusion-{namespace}-namespace-preferences')

  def get_all_applications(self, namespace: str):
    return self._load_json(f'datafusion-{namespace}-applications')

  def get_application_preferences(self, namespace: str, application_name: str):
    return self._load_json(
        f'datafusion-{namespace}-application-{application_name}-preferences')
