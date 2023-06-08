""" Tests for search expressions for LogsQuery """
from unittest import TestCase

from .search_exprs import AnyREFound, Equals, REFound


class TestEquals(TestCase):
  """ Test Equals search expression """

  def test_stackdriver_expr(self):
    expr = Equals(field='hello', value='world')
    self.assertEqual(expr.stackdriver_expr, 'hello="world"')

  def test_field_equals(self):
    entry = {'hello': 'world'}
    expr = Equals(field='hello', value='world')
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_field_not_equals(self):
    entry = {'hello': 'world'}
    expr = Equals(field='hello', value='42')
    self.assertFalse(expr.is_log_entry_matches(entry))

  def test_nested_stackdriver_expr(self):
    expr = Equals(field='one.two.three', value='four')
    self.assertEqual(expr.stackdriver_expr, 'one.two.three="four"')

  def test_nested_field_equals(self):
    entry = {'one': {'two': {'three': 'four'}}}
    expr = Equals(field='one.two.three', value='four')
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_nested_field_not_equals(self):
    entry = {'one': {'two': {'three': 'four'}}}
    expr = Equals(field='one.two.three', value='five')
    self.assertFalse(expr.is_log_entry_matches(entry))


class TestREFound(TestCase):
  """ Test TestREFound search expression """

  def test_stackdriver_expr(self):
    expr = REFound(field='hello', re_exp='.*world.*')
    self.assertEqual(expr.stackdriver_expr, 'hello=~".*world.*"')

  def test_found(self):
    entry = {'one': 'two three four'}
    expr = REFound(field='one', re_exp='.*three.*')
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_not_found(self):
    entry = {'one': 'two three four'}
    expr = REFound(field='one', re_exp='.*five.*')
    self.assertFalse(expr.is_log_entry_matches(entry))

  def test_nested_stackdriver_expr(self):
    expr = REFound(field='one.two.three', re_exp='.*four.*')
    self.assertEqual(expr.stackdriver_expr, 'one.two.three=~".*four.*"')

  def test_nested_found(self):
    entry = {'one': {'two': {'three': 'four five six'}}}
    expr = REFound(field='one.two.three', re_exp='.*five.*')
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_nested_not_found(self):
    entry = {'one': {'two': {'three': 'four five six'}}}
    expr = REFound(field='one.two.three', re_exp='.*seven.*')
    self.assertFalse(expr.is_log_entry_matches(entry))


class TestAnyREFound(TestCase):
  """ Test TestAnyREFound search expression """

  def test_stackdriver_expr_one_re(self):
    expr = AnyREFound(field='one', re_exps=['.*two.*'])
    self.assertEqual(expr.stackdriver_expr, 'one=~(".*two.*")')

  def test_stackdriver_expr_many_res(self):
    expr = AnyREFound(field='one', re_exps=['.*two.*', 'three', 'four'])
    self.assertEqual(expr.stackdriver_expr,
                     'one=~(".*two.*" OR "three" OR "four")')

  def test_found(self):
    entry = {'one': 'two three four'}
    expr = AnyREFound(field='one', re_exps=['.*three.*', '.*five.*', '.*six.*'])
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_not_found(self):
    entry = {'one': 'two three four'}
    expr = AnyREFound(field='one', re_exps=['.*five.*', '.*six.*', '.*seven.*'])
    self.assertFalse(expr.is_log_entry_matches(entry))

  def test_nested_stackdriver_expr_many_res(self):
    expr = AnyREFound(field='one.two.three',
                      re_exps=['.*four.*', 'five', 'six'])
    self.assertEqual(expr.stackdriver_expr,
                     'one.two.three=~(".*four.*" OR "five" OR "six")')

  def test_nested_found(self):
    entry = {'one': {'two': {'three': 'five four six'}}}
    expr = AnyREFound(field='one.two.three',
                      re_exps=['.*four.*', '.*seven.*', '.*eight.*'])
    self.assertTrue(expr.is_log_entry_matches(entry))

  def test_nested_not_found(self):
    entry = {'one': {'two': {'three': 'five four six'}}}
    expr = AnyREFound(field='one.two.three',
                      re_exps=['.*seven.*', '.*eight.*', '.*nine.*'])
    self.assertFalse(expr.is_log_entry_matches(entry))
