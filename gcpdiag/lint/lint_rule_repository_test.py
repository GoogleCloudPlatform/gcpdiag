'Tests for LintRuleRepository'

from functools import cached_property

import pytest

from gcpdiag.lint import LintRuleRepository, LintRulesPattern


class FakePyPkg:

  def __init__(self, name, path):
    self.__name__ = name
    self.__path__ = path


class FakeModulesGateway:
  'Testing double to mock interactions with python modules'

  def __init__(self, modules_by_name):
    self.modules_by_name = modules_by_name

  def list_pkg_modules(self, pkg):
    return [
        k for k in self.modules_by_name.keys() if k.startswith(pkg.__name__)
    ]

  def get_module(self, name):
    return self.modules_by_name[name]


class FakeModule:
  'Testing double to mock interactions with python module'

  def __init__(self, methods, doc):
    self.methods_by_name = methods
    self.doc = doc

  def get_method(self, name):
    return self.methods_by_name.get(name)

  def get_module_doc(self):
    return self.doc

  def get_attr(self, attribute):
    return attribute


class FakeExecutionStrategy:
  """ Simple testing double for ExecutionStrategy """

  def __init__(self):
    self.executed_rules = None

  def filter_runnable_rules(self, rules):
    return rules

  def run_rules(self, context, result, rules):
    del context, result
    self.executed_rules = rules


class Setup:
  'Helper class to instantiate testing subj and its dependencies'

  def __init__(self,
               modules_by_name,
               load_extended=None,
               include=None,
               exclude=None):
    self.modules_by_name = modules_by_name
    self.load_extended = load_extended
    self.include = include
    self.exclude = exclude

  @cached_property
  def repo(self):
    return LintRuleRepository(load_extended=self.load_extended,
                              modules_gateway=self.modules_gw,
                              execution_strategy=self.execution_strategy,
                              exclude=self.exclude,
                              include=self.include)

  @cached_property
  def modules_gw(self):
    return FakeModulesGateway(self.modules_by_name)

  @cached_property
  def execution_strategy(self):
    return FakeExecutionStrategy()


def mk_simple_rule_module(methods=None, doc=None):
  methods = methods or {'run_rule': lambda context, rule_report: None}
  doc = doc or 'hello world, fake module'
  return FakeModule(methods=methods, doc=doc)


def mk_simple_async_rule_module(methods=None, doc=None):
  methods = methods or {'async_run_rule': lambda context, rule_report: None}
  doc = doc or 'hello world, fake module'
  return FakeModule(methods=methods, doc=doc)


def test_sync_happy_path():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()

  setup = Setup(
      modules_by_name={
          'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
          'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2
      })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 2
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') in executed_run_rule_fs


def test_async_happy_path():
  fake_module1 = mk_simple_async_rule_module()
  fake_module2 = mk_simple_async_rule_module()

  setup = Setup(
      modules_by_name={
          'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
          'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2
      })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 2
  executed_run_rule_fs = [
      r.async_run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('async_run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('async_run_rule') in executed_run_rule_fs


def test_no_entrypoint_raises():
  fake_module1 = mk_simple_rule_module(methods={'dummy': lambda: None})

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
  })

  with pytest.raises(RuntimeError):
    setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))


def test_wrong_rule_class_raises():
  fake_module1 = mk_simple_rule_module()

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.hello_2022_001_hello': fake_module1,
  })

  with pytest.raises(ValueError):
    setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))


def test_wrong_module_names_ignored():
  fake_module1 = mk_simple_rule_module()

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_hello': fake_module1,
  })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 0


def test_tests_ignored():
  fake_module1 = mk_simple_rule_module()

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello_test': fake_module1,
  })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 0


def test_empty_doc_raises():
  fake_module1 = FakeModule(
      methods={'run_rule': lambda context, rule_report: None}, doc='')

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
  })

  with pytest.raises(RuntimeError):
    setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))


def test_singleline_doc_happy_path():
  fake_module1 = FakeModule(
      methods={'run_rule': lambda context, rule_report: None}, doc='first line')

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
  })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  assert setup.execution_strategy.executed_rules[0].short_desc == 'first line'
  assert setup.execution_strategy.executed_rules[0].long_desc == ''


def test_multiline_doc_happy_path():
  fake_module1 = FakeModule(
      methods={'run_rule': lambda context, rule_report: None},
      doc='first line \n\n third line \n fourth line')

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
  })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  assert setup.execution_strategy.executed_rules[0].short_desc == 'first line '
  assert setup.execution_strategy.executed_rules[
      0].long_desc == ' third line \n fourth line'


def test_non_empty_second_doc_line_raises():
  fake_module1 = FakeModule(
      methods={'run_rule': lambda context, rule_report: None},
      doc='first line \n second line \n third line \n fourth line')

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
  })

  with pytest.raises(RuntimeError):
    setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))


def test_ext_ignored():
  fake_module1 = mk_simple_rule_module()

  setup = Setup(modules_by_name={
      'gcpdiag.lint.fakeprod.err_ext_2022_001_hello': fake_module1,
  })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 0


def test_ext_loaded():
  fake_module1 = mk_simple_rule_module()

  setup = Setup(load_extended=True,
                modules_by_name={
                    'gcpdiag.lint.fakeprod.err_ext_2022_001_hello':
                        fake_module1,
                })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1


def test_include_id():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()

  setup = Setup(include=[LintRulesPattern('fakeprod/ERR/2022_001')],
                modules_by_name={
                    'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
                    'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2
                })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') not in executed_run_rule_fs


def test_include_class():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()

  setup = Setup(include=[LintRulesPattern('fakeprod/ERR/*')],
                modules_by_name={
                    'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
                    'gcpdiag.lint.fakeprod.warn_2022_002_world': fake_module2
                })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') not in executed_run_rule_fs


def test_include_product():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()
  fake_module3 = mk_simple_rule_module()

  setup = Setup(
      include=[LintRulesPattern('fakeprod/*/*')],
      modules_by_name={
          'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
          'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2,
          'gcpdiag.lint.anotherfakeprod.err_2022_001_hihi': fake_module3
      })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.anotherfakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 2
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') in executed_run_rule_fs


def test_exclude_id():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()

  setup = Setup(exclude=[LintRulesPattern('fakeprod/ERR/2022_002')],
                modules_by_name={
                    'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
                    'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2
                })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') not in executed_run_rule_fs


def test_exclude_class():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()

  setup = Setup(exclude=[LintRulesPattern('fakeprod/WARN/*')],
                modules_by_name={
                    'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
                    'gcpdiag.lint.fakeprod.warn_2022_002_world': fake_module2
                })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') not in executed_run_rule_fs


def test_exclude_product():
  fake_module1 = mk_simple_rule_module()
  fake_module2 = mk_simple_rule_module()
  fake_module3 = mk_simple_rule_module()

  setup = Setup(
      exclude=[LintRulesPattern('fakeprod/*/*')],
      modules_by_name={
          'gcpdiag.lint.fakeprod.err_2022_001_hello': fake_module1,
          'gcpdiag.lint.fakeprod.err_2022_002_world': fake_module2,
          'gcpdiag.lint.anotherfakeprod.err_2022_001_hihi': fake_module3
      })

  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.fakeprod', 'fake.path'))
  setup.repo.load_rules(FakePyPkg('gcpdiag.lint.anotherfakeprod', 'fake.path'))
  setup.repo.run_rules(context=None)

  assert len(setup.execution_strategy.executed_rules) == 1
  executed_run_rule_fs = [
      r.run_rule_f for r in setup.execution_strategy.executed_rules
  ]
  assert fake_module1.get_method('run_rule') not in executed_run_rule_fs
  assert fake_module2.get_method('run_rule') not in executed_run_rule_fs
  assert fake_module3.get_method('run_rule') in executed_run_rule_fs
