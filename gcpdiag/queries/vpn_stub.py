# Copyright 2021 Google LLC
"""Stub API calls used in vpn.py for testing."""

from gcpdiag.queries import apis_stub

# pylint: disable=invalid-name
# pylint: disable=unused-argument


class VpnApiStub:

  def vpnTunnels(self):
    return self

  def get(self, project, region, vpnTunnel):
    return apis_stub.RestCallStub(project, vpnTunnel)


class VpnTunnelApiStub(apis_stub.ApiStub):
  """Mock object to simulate VPN tunnel api calls."""

  def __init__(self, mock_state):
    self.mock_state = mock_state

  def get(self, project, region, vpnTunnel):
    if self.mock_state == 'vpnTunnels':
      return apis_stub.RestCallStub(project, vpnTunnel)
    else:
      raise ValueError(f'cannot call method {self.mock_state} here')
