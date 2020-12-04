# Lint as: python3
"""Test code in utils.py."""
from googleapiclient import errors

from gcp_doctor import utils

# https://github.com/googleapis/google-api-python-client/blob/master/tests/test_errors.py
JSON_ERROR_CONTENT = b"""
{
 "error": {
  "message": "country is required"
 }
}
"""


def test_is_region():
  """is_region() should return correct result when presented with region or zone string."""
  assert utils.is_region('us-central1')
  assert not utils.is_region('us-central1-b')


def test_http_error_message():
  """http_error_message extracts properly an error from a Google API JSON string."""
  error = errors.HttpError(content=JSON_ERROR_CONTENT, resp=None)
  result = utils.http_error_message(error)
  expected = 'country is required'
  assert result == expected
