# Copyright 2025 Google LLC
# ... (standard license header) ...
"""Unit tests for vpn.py."""

from unittest import mock

import pytest
from googleapiclient import errors

from gcpdiag import caching, utils
from gcpdiag.queries import apis_stub, vpn, vpn_stub

DUMMY_PROJECT_ID = 'gcpdiag-vpn1-aaaa'
DUMMY_VPN_NAME = 'vpn-tunnel-1'
DUMMY_REGION = 'europe-west4'


def get_api_stub(service_name, version, project_id=None):
  if service_name == 'compute':
    return vpn_stub.VpnApiStub()
  return apis_stub.get_api_stub(service_name, version, project_id)


@mock.patch('gcpdiag.queries.apis.get_api', new=get_api_stub)
class Test:

  def test_get_vpn(self):
    tunnel = vpn.get_vpn(project_id=DUMMY_PROJECT_ID,
                         vpn_name=DUMMY_VPN_NAME,
                         region=DUMMY_REGION)

    assert tunnel.name == 'vpn-tunnel-1'
    assert tunnel.status == 'ESTABLISHED'
    assert tunnel.id == '123456789'
    assert tunnel.peer_ip == '1.1.1.1'
    assert tunnel.project_id == DUMMY_PROJECT_ID
    assert 'europe-west4' in tunnel.full_path
    assert tunnel.local_traffic_selector == ['0.0.0.0/0']
    assert tunnel.remote_traffic_selector == ['0.0.0.0/0']

  def test_short_path(self):
    tunnel = vpn.get_vpn(DUMMY_PROJECT_ID, DUMMY_VPN_NAME, DUMMY_REGION)
    assert tunnel.short_path == f'{DUMMY_PROJECT_ID}/{DUMMY_VPN_NAME}'

  def test_get_vpn_failure(self):

    mock_request = mock.Mock()
    mock_request.execute.side_effect = errors.HttpError(mock.Mock(status=404),
                                                        b'Test Error')

    mock_service = mock.Mock()
    mock_service.vpnTunnels.return_value.get.return_value = mock_request

    # Overlay the class-level patch with a new one for this test
    with mock.patch('gcpdiag.queries.apis.get_api', return_value=mock_service):
      with caching.bypass_cache():

        with pytest.raises(utils.GcpApiError):
          vpn.get_vpn(DUMMY_PROJECT_ID, DUMMY_VPN_NAME, DUMMY_REGION)
