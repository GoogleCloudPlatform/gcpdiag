# Lint as: python3
"""Test code in utils.py."""
from gcp_doctor import utils


def test_is_region():
  """is_region() should return correct result when presented with region or zone string."""
  assert utils.is_region('us-central1')
  assert not utils.is_region('us-central1-b')
