# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Main runbook module containing core functionality implementation"""

import dataclasses
import importlib
import inspect
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from gcpdiag import config, models
from gcpdiag.runbook import constants, util
from gcpdiag.runbook.flags import INTERACTIVE_MODE
from gcpdiag.runbook.output.base_output import BaseOutput
from gcpdiag.runbook.output.terminal_output import TerminalOutput


@dataclasses.dataclass
class StepResult:
  """Runbook Step Results"""
  status: str
  resource: Optional[models.Resource]
  step: str
  reason: Optional[str]
  remediation: Optional[str]
  remediation_skipped: Optional[bool]
  start_time_utc: float
  end_time_utc: float
  prompt_response: Any

  def __init__(self,
               status: str,
               resource: Optional[models.Resource],
               step: str,
               reason: Optional[str],
               remediation: Optional[str],
               remediation_skipped: Optional[bool] = False,
               prompt_response: Optional[Any] = None):
    self.status = status
    self.resource = resource
    self.step = step
    self.reason = reason
    self.remediation = remediation
    self.remediation_skipped = True if config.get(
        'auto') else remediation_skipped

    self.prompt_response = prompt_response

  def __hash__(self) -> int:
    return str(self.status + str(self.resource or '') + str(self.step) +
               (self.remediation or '') + (self.reason or '')).__hash__()

  def __eq__(self, other) -> bool:
    if self.__class__ == other.__class__:
      return (self.status == other.status and self.step == other.step and
              self.resource == other.resource and
              self.reason == other.reason and
              self.remediation == other.remediation)
    else:
      return False


class ReportManager:
  """Base Report Manager subclassed to hand different interfaces (cli, api)"""
  results: Dict[str, StepResult]

  def __init__(self) -> None:
    self.results = {}
    self.tree = None

  def add_step_result(self, result: StepResult):
    pass

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = {}
    for step_result in self.results.values():
      totals[step_result.status] = totals.get(step_result.status, 0) + 1
    return totals

  def generate_report(self) -> None:
    pass

  @property
  def any_failed(self) -> bool:
    return any(
        r.status in ('failed', 'uncertain') for r in self.results.values())


class TerminalReportManager(ReportManager):
  """ Class representing results of runbook """
  report_path: str

  def __init__(self) -> None:
    super().__init__()
    self.report_path = ''

  def get_rule_statuses(self) -> Dict[str, str]:
    return {str(r.step): r.status for r in self.results.values()}

  def add_step_result(self, result: StepResult):
    self.results[result.step] = result

  def get_report_path(self):
    date = datetime.now(timezone.utc).strftime('%Y_%m_%d_%H_%M_%S_%Z')
    report_name = f'gcpdiag_runbook_report_{self.tree.name.replace("/","_")}_{date}.json'
    self.report_path = os.path.join(config.get('report_dir'), report_name)

  def generate_report(self):
    """Generate Runbook Report"""
    # Always generate a report to avoid FileNotFound, even if there are no failed rules
    if not self.report_path:
      self.get_report_path()
    result = self._generate_json_report()
    if config.get('interface') == 'cli':
      self._write_report_to_terminal(result)

  def _generate_json_report(self):

    def result_to_dict(result: StepResult):
      return {
          'step':
              result.step,
          'resource':
              result.resource.short_path if result.resource else '-',
          'status':
              result.status,
          'reason':
              result.reason,
          'remediation':
              result.remediation if result.remediation else '-',
          'remediation_skipped':
              False if config.get('auto') else result.remediation_skipped,
          'start_time_utc':
              result.start_time_utc,
          'end_time_utc':
              result.end_time_utc
      }

    report = {
        'runbook': self.tree.name,
        'totals_by_status': self.get_totals_by_status(),
        'execution_mode': 'auto' if config.get('auto') else 'interactive',
        'results': list(self.results.values())
    }
    return json.dumps(report,
                      ensure_ascii=False,
                      default=result_to_dict,
                      indent=2)

  def _write_report_to_terminal(self, json_report):
    try:
      with open(self.report_path, 'w', encoding='utf-8') as file:
        file.write(json_report)
    except PermissionError as e:
      logging.error(
          'Permission denied while saving report to file, displaying report')
      logging.debug(e)
      print(json_report, file=sys.stderr)
    except OSError as e:
      logging.error(
          'Failed to save generated report to file, displaying report')
      logging.debug(e)
      print(json_report, file=sys.stderr)
    else:
      print(f'\nRunbook report located in: {file.name}', file=sys.stderr)


class InteractionInterface:
  """
  RunbookRule workflow use this interface to report ongoing results.
  """
  rm: ReportManager
  output: BaseOutput

  def __init__(self, output=None) -> None:
    self.output: BaseOutput = output or TerminalOutput()

  def set_dt(self, rule):
    self.rule = rule

  def get_calling_step(self):
    # add report // task
    calling_frame = inspect.currentframe().f_back.f_back.f_back
    if calling_frame:
      idz = calling_frame.f_locals.get('self').run_id
      return idz

  def prompt(self,
             message: str,
             kind: str = '',
             options: dict = None,
             choice_msg: str = '') -> None:
    return self.output.prompt(message=message,
                              kind=kind,
                              options=options,
                              choice_msg=choice_msg)

  def info(self,
           message: str,
           resource=None,
           store_in_report=False,
           step_type='INFO') -> None:
    step = step_type or util.get_caller_object(2)
    self.output.info(message=message, step_type=step_type)
    if store_in_report:
      self.rm.add_step_result(
          StepResult(status='info',
                     resource=resource,
                     step=step.run_id,
                     reason=message,
                     remediation=''))

  def prepare_rca(self, resource: Optional[models.Resource], template, suffix,
                  context) -> None:
    step = util.get_caller_object(2)
    try:
      module = importlib.import_module(step.__module__)
      file_name = module.__file__
    except ImportError as e:
      logging.error(e)
    except AttributeError as e:
      logging.error('failed to locate steps module %s', e)
    else:
      file, prefix = template.split('::')
      if file_name:
        filepath = '/'.join([os.path.dirname(file_name), 'templates'])
        rca = util.render_template(filepath, f'{file}.jinja', context, prefix,
                                   suffix)
        self.output.info(message=rca)
        self.rm.add_step_result(
            StepResult(status='rca',
                       resource=resource,
                       step=step.run_id,
                       reason=rca,
                       remediation=''))

  def add_skipped(self, resource: Optional[models.Resource],
                  reason: str) -> None:
    step = util.get_caller_object(2)
    self.output.print_skipped(resource=resource, reason=reason)
    self.rm.add_step_result(
        StepResult(status='skipped',
                   resource=resource,
                   step=step.run_id,
                   reason=reason,
                   remediation=''))

  def add_ok(self, resource: models.Resource, reason: str = '') -> None:
    step = util.get_caller_object(2)
    self.output.print_ok(resource=resource, reason=reason)
    self.rm.add_step_result(
        StepResult(status='ok',
                   resource=resource,
                   step=step.run_id,
                   reason=reason,
                   remediation=''))

  def add_failed(self,
                 resource: models.Resource,
                 reason: str,
                 remediation: str,
                 human_task_msg: str = '') -> Any:
    """Output test result and registers the result to be used in
    the runbook report.

    The failure assigned a human task unless program is running
    autonomously
    """
    step = util.get_caller_object(2)
    self.output.print_failed(resource=resource,
                             reason=reason,
                             remediation=remediation)
    result = StepResult(status='failed',
                        resource=resource,
                        reason=reason,
                        step=step.run_id,
                        remediation=remediation)
    # Add results to report manager so other dependent features can act on it.
    self.rm.add_step_result(result)
    # assign a human task to be completed
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)
    if not config.get(INTERACTIVE_MODE):
      result.prompt_response = choice

      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice

  def add_uncertain(self,
                    resource: models.Resource,
                    reason: str,
                    remediation: str = None,
                    human_task_msg: str = '') -> Any:
    step = util.get_caller_object(2)
    self.output.print_uncertain(reason=reason,
                                resource=resource,
                                remediation=remediation)
    result = StepResult(status='uncertain',
                        resource=resource,
                        reason=reason,
                        step=step.run_id,
                        remediation=remediation)
    self.rm.add_step_result(result)
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)

    if not config.get(INTERACTIVE_MODE):
      result.prompt_response = choice
      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice
