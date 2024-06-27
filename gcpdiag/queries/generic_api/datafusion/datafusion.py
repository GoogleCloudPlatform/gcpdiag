"""Gateway for Datafusion service"""

from gcpdiag.queries.generic_api.api_build import api


class Datafusion(api.API):
  """Gateway for Datafusion service"""

  def __init__(self, base_url: str, creds: api.Creds,
               retry_strategy: api.RetryStrategy) -> None:
    super().__init__(base_url, creds, retry_strategy)

  def get_system_profiles(self):
    endpoint = 'v3/profiles'
    return self.get(endpoint)

  def get_all_namespaces(self):
    endpoint = 'v3/namespaces'
    return self.get(endpoint)

  def get_user_profiles(self, namespace: str):
    endpoint = f'v3/namespaces/{namespace}/profiles'
    return self.get(endpoint)
