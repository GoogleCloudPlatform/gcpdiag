# Lint as: python3
"""Test code in utils.py."""
import pytest
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


class TestGcpApiError():

  def test_exception(self):
    """GcpApiError correctly formats an error from a Google API JSON string."""
    with pytest.raises(utils.GcpApiError) as api_error:
      mocked_error = errors.HttpError(content=JSON_ERROR_CONTENT, resp=None)
      raise utils.GcpApiError(mocked_error)
    assert 'country is required' in str(api_error.value)


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


def test_is_full_res_name():
  """is_full_res_name() should return correct result for a valid/unvalid full resource name."""
  assert utils.is_full_res_name(
      'https://library.googleapis.com/shelves/shelf1/books/book2')
  assert utils.is_full_res_name('//googleapis.com/shelves/shelf1/books/book2')
  assert not utils.is_full_res_name('shelves/shelf1/books/book2')


def test_is_rel_res_name():
  """is_rel_res_name() should return correct result for a valid/unvalid relative resource name."""
  assert not utils.is_rel_res_name(
      '//library.googleapis.com/shelves/shelf1/books/book2')
  assert utils.is_rel_res_name(
      'projects/testproject/locations/us-central1/keyRings/usckr')


def test_is_valid_res_name():
  """is_valid_res_name() should return correct result for a valid/unvalid resource name."""
  assert utils.is_valid_res_name('//googleapis.com/shelves/shelf1/books/book2')
  assert utils.is_valid_res_name('//googleapis.com/shelves/shelf1/books/2')
  assert utils.is_valid_res_name('shelves/shelf1/books/book2')
  assert not utils.is_valid_res_name(
      'googleapis.com/shelves/shelf1/books/book2')
  assert not utils.is_valid_res_name('//googleapis.com/shelves/shelf1/books/-')
  assert not utils.is_valid_res_name('//googleapis.com/shelves/shelf1/2/2')
  assert not utils.is_valid_res_name('shelves/shelf1/books')
  assert not utils.is_valid_res_name('googleapis.com/shelves')
  assert not utils.is_valid_res_name('googleapis')


def test_get_region_by_res_name():
  """get_region_by_res_name() should extract a region name from a resource name."""
  result = utils.get_region_by_res_name(
      'projects/testproject/locations/us-central1/keyRings/usckr')
  assert result == 'us-central1'


def test_get_zone_by_res_name():
  """get_zone_by_res_name() should extract a zone name from a resource name."""
  result = utils.get_zone_by_res_name(
      'projects/testproject/zones/us-central1-c/keyRings/usckr')
  assert result == 'us-central1-c'


def test_get_project_by_res_name():
  """get_project_by_res_name() should extract a project name from a resource name."""
  result = utils.get_project_by_res_name(
      'projects/testproject/locations/us-central1/keyRings/usckr')
  assert result == 'testproject'


def test_extract_value_from_res_name():
  """extract_value_from_res_name() should extract a value by a given key from a resource name."""
  result = utils.extract_value_from_res_name(
      'projects/testproject/locations/us-central1/keyRings/usckr', 'keyRings')
  assert result == 'usckr'
  with pytest.raises(ValueError):
    utils.extract_value_from_res_name('', 'keyRings')
  with pytest.raises(ValueError):
    utils.extract_value_from_res_name(
        'projects/testproject/locations/us-central1', 'us-central1')
