# Lint as: python3
"""Test code in utils.py."""
from gcp_doctor import utils


def test_is_region():
  assert utils.is_region('us-central1')
  assert not utils.is_region('us-central1-b')
