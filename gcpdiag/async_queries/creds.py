"""
  Adapter between gcpdiag.async_queries.api.Creds protocol and
  gcpdiag.queries.apis._get_credentials
"""
from gcpdiag.queries import apis


class GcpdiagCreds:
  """
    Adapter between gcpdiag.async_queries.api.Creds protocol and
    gcpdiag.queries.apis._get_credentials
  """

  def get_token(self) -> str:
    # pylint: disable=protected-access
    return apis._get_credentials().token
