""" Search terms for LogsQueres """
import re
from functools import cached_property

from boltons.iterutils import get_path


class Equals:
  """
  Filter log entries that has field=value

  Example:
    query = LogsQuery(
      ...
      search_exprs=[
        Equals(
          field='labels.hello.world',
          value='forty two',
        ),
      ],
      ...
    )
    query.mk_query()
  """

  def __init__(self, field, value):
    self._field = field
    self._value = value

  @property
  def stackdriver_expr(self):
    return f'{self._field}="{self._value}"'

  def is_log_entry_matches(self, log_entry):
    value = get_path(log_entry, self._field.split('.'), default=None)
    if value is None:
      return False
    return value == self._value


class REFound:
  """
  Filter log entries that contain specified regex in the specified field

  Example:
    query = LogsQuery(
      ...
      search_exprs=[
        REFound(
          field='labels.hello.world',
          re_exp='Hello.*World',
        ),
      ],
      ...
    )
    query.mk_query()
  """

  def __init__(self, field, re_exp):
    self._field = field
    self._re_exp = re_exp

  @property
  def stackdriver_expr(self):
    return f'{self._field}=~"{self._re_exp}"'

  def is_log_entry_matches(self, log_entry):
    value = get_path(log_entry, self._field.split('.'), default=None)
    return bool(self._compiled_re.search(value))

  @cached_property
  def _compiled_re(self):
    return re.compile(self._re_exp)


class AnyREFound:
  """
  Filter log entries that contain any of the specified regexes in the
  specified field

  Example:
    query = LogsQuery(
      ...
      search_exprs=[
        AnyREFound(
          field='labels.hello.world',
          re_exps=[
            'Hello.*World',
            'world.*hello',
            'something [Ee]lse',
          ],
        ),
      ],
      ...
    )
    query.mk_query()
  """

  def __init__(self, field, re_exps):
    self._field = field
    self._re_exps = re_exps

  @property
  def stackdriver_expr(self):
    return '{field}=~({re_list})'.format(field=self._field,
                                         re_list=' OR '.join(
                                             f'"{p}"' for p in self._re_exps))

  def is_log_entry_matches(self, log_entry):
    value = get_path(log_entry, self._field.split('.'), default=None)
    return any(r.search(value) for r in self._compiled_re_exps)

  @cached_property
  def _compiled_re_exps(self):
    return [re.compile(p) for p in self._re_exps]
