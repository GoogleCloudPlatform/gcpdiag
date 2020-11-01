# Lint as: python3
"""Various utility functions."""

import re

REGION_MATCH = re.compile(r'^\w+-\w+$', re.ASCII)


def is_region(name: str) -> bool:
  if re.match(REGION_MATCH, name):
    return True
  else:
    return False
