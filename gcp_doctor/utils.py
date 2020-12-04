# Lint as: python3
"""Various utility functions."""

import json
import re

from googleapiclient import errors


def is_region(name: str) -> bool:
  return bool(re.match(r'^\w+-\w+$', name))


# see also: https://github.com/googleapis/google-api-python-client/issues/662
def http_error_message(err: errors.HttpError) -> str:
  content = json.loads(err.content)
  if isinstance(content,
                dict) and 'error' in content and 'message' in content['error']:
    return content['error']['message']
  else:
    return str(err)
