"""
Returns project-wide rule classes list
"""
from typing import Dict


def get_rule_classes() -> Dict:

  return {
      'BP': 'Best practice, opinionated recommendation',
      'ERR': 'Something that is very likely to be wrong',
      'WARN': 'Something that is possibly wrong',
      'SEC': 'Potential security issue',
      # classes for extended rules
      'BP_EXT': '(Extended) Best practice, opinionated recommendation',
      'ERR_EXT': '(Extended) Something that is very likely to be wrong',
      'WARN_EXT': '(Extended) Something that is possibly wrong',
      'SEC_EXT': '(Extended) Potential security issue',
  }
