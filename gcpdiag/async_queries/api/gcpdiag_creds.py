"""
  Adapter between gcpdiag.async_queries.api.Creds protocol and
  gcpdiag.queries.apis.get_credentials
"""

from typing import Any, Dict

import google.auth.transport.requests  # type: ignore

from gcpdiag.queries import apis


def refresh_google_auth_creds(creds: Any) -> None:
  request = google.auth.transport.requests.Request()
  creds.refresh(request)


class GcpdiagCreds:
  """
    Adapter between gcpdiag.async_queries.api.Creds protocol and
    gcpdiag.queries.apis.get_credentials
  """

  def update_headers(self, headers: Dict[str, str]) -> None:
    creds = apis.get_credentials()
    if not creds.token:
      refresh_google_auth_creds(creds)
    headers['Authorization'] = f'Bearer {creds.token}'
