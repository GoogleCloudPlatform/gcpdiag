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

import collections
import dataclasses
import importlib
import json
import logging
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from gcpdiag import config, models
from gcpdiag.runbook import constants, util
from gcpdiag.runbook.flags import INTERACTIVE_MODE
from gcpdiag.runbook.output.base_output import BaseOutput
from gcpdiag.runbook.output.terminal_output import TerminalOutput


@dataclasses.dataclass
class ResourceEvaluation:
  """Observation on a single GCP resource"""
  resource: Optional[models.Resource]
  reason: Optional[str]
  remediation: Optional[str]
  remediation_skipped: Optional[bool]
  prompt_response: Optional[str]
  status: str

  def __init__(self,
               status: str,
               resource: Optional[models.Resource],
               reason: Optional[str],
               remediation: Optional[str],
               remediation_skipped: Optional[bool] = None,
               prompt_response: Optional[str] = None):
    self.status = status
    self.resource = resource
    self.reason = reason
    self.remediation = remediation
    self.remediation_skipped = True if config.get(
        'auto') else remediation_skipped
    self.prompt_response = prompt_response


@dataclasses.dataclass
class StepResult:
  """Runbook Step Results"""
  # if any evals failed this will be failed
  execution_id: str
  start_time_utc: float
  end_time_utc: float
  results: List[ResourceEvaluation]
  prompt_response: Any
  metadata: dict
  info: List

  def __init__(self, step):
    self.execution_id = step.execution_id
    self.step = step
    self.prompt_response = None
    self.results = []
    self.metadata = OrderedDict()
    self.info = []

  def __hash__(self) -> int:
    return self.execution_id.__hash__()

  def __eq__(self, other) -> bool:
    if self.__class__ == other.__class__:
      return (self.execution_id == other.execution_id and
              self.overall_status == other.overall_status and
              self.results == other.results and
              self.metadata == other.metadata and self.info == other.info)
    else:
      return False

  @property
  def overall_status(self):
    """Return the worst status available in the evaluations for the step

    Order of worst evals: failed > uncertain > ok > skipped
    """
    for status in constants.STATUS_ORDER:
      if self.totals_by_status.get(status):
        return status
    return 'NO_STATUS'

  @property
  def any_failed(self):
    return any(r.status == 'failed' for r in self.results)

  @property
  def any_uncertain(self):
    return any(r.status == 'uncertain' for r in self.results)

  @property
  def totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = collections.defaultdict(int)
    for r in self.results:
      totals[r.status] += 1
    return totals


class ReportManager:
  """Base Report Manager subclassed to hand different interfaces (cli, api)"""
  results: Dict[str, StepResult]

  def __init__(self) -> None:
    self.results = {}
    self.tree = None

  def add_step_result(self, result: StepResult):
    self.results[result.execution_id] = result

  def add_step_eval(self, execution_id, evaluation: ResourceEvaluation):
    self.results[execution_id].results.append(evaluation)

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = collections.defaultdict(int)
    for step_result in self.results.values():
      totals[step_result.overall_status] += 1
    return totals

  def generate_report(self, operator) -> None:
    pass

  @property
  def any_failed(self) -> bool:
    return any(r.overall_status in ('failed', 'uncertain')
               for r in self.results.values())

  def add_step_metadata(self, key, value, step_execution_id):
    if step_execution_id:
      step_result = self.results[step_execution_id]
    if step_result:
      step_result.metadata[key] = value

  def add_step_info_metadata(self, value, step_execution_id):
    if step_execution_id:
      step_result = self.results[step_execution_id]
    if step_result:
      step_result.info.append(value)

  def get_step_metadata(self, key, step_execution_id):
    if step_execution_id:
      step_result = self.results[step_execution_id]
    if step_result:
      return step_result.metadata.get(key)
    return None

  def get_all_step_metadata(self, step_execution_id) -> dict:
    if step_execution_id:
      step_result = self.results[step_execution_id]
    if step_result:
      return step_result.metadata
    return {}


class TerminalReportManager(ReportManager):
  """ Class representing results of runbook """
  report_path: str

  def __init__(self) -> None:
    super().__init__()
    self.report_path = ''

  def get_rule_statuses(self) -> Dict[str, str]:
    return {
        str(r.execution_id): r.overall_status for r in self.results.values()
    }

  def get_report_path(self):
    date = datetime.now(timezone.utc).strftime('%Y_%m_%d_%H_%M_%S_%Z')
    tree_name = self.tree.name
    report_name = f"gcpdiag_runbook_report_{re.sub(r'[/-]', '_', tree_name)}_{date}.json"
    self.report_path = os.path.join(config.get('report_dir'), report_name)

  def generate_report(self, operator):
    """Generate Runbook Report"""
    # Always generate a report to avoid FileNotFound, even if there are no failed rules
    if not self.report_path:
      self.get_report_path()
    result = self._generate_json_report(operator)
    if config.get('interface') == 'cli':
      self._write_report_to_terminal(result)

  def _generate_json_report(self, operator):

    def resource_evaluation(eval_list: List[ResourceEvaluation]):
      return [{
          'resource':
              r.resource.full_path if r.resource else '-',
          'status':
              r.status,
          'reason':
              r.reason,
          'remediation':
              r.remediation if r.remediation else '-',
          'remediation_skipped':
              False if config.get('auto') else r.remediation_skipped
      } for r in eval_list]

    def result_to_dict(entry: StepResult):
      return {
          'execution_id': entry.step.execution_id,
          'totals_by_status': entry.totals_by_status,
          'description': entry.step.__doc__,
          'execution_message': entry.step.execution_message,
          'overall_status': entry.overall_status,
          'start_time_utc': entry.start_time_utc,
          'end_time_utc': entry.end_time_utc,
          'metadata': entry.metadata,
          'info': entry.info,
          'resource_evaluation': resource_evaluation(entry.results)
      }

    def parse_report_data(data):
      if isinstance(data, StepResult):
        return result_to_dict(data)
      else:
        return str(data)

    report = {
        'runbook': self.tree.name,
        'parameters': operator.parameters,
        'totals_by_status': self.get_totals_by_status(),
        'execution_mode': 'auto' if config.get('auto') else 'interactive',
        'results': self.results
    }

    return json.dumps(report,
                      ensure_ascii=False,
                      default=parse_report_data,
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

  def prompt(self,
             message: str,
             kind: str = '',
             options: dict = None,
             choice_msg: str = '') -> None:
    return self.output.prompt(message=message,
                              kind=kind,
                              options=options,
                              choice_msg=choice_msg)

  def info(self, message: str, step_type='INFO') -> None:
    self.output.info(message=message, step_type=step_type)

  def prepare_rca(self, resource: Optional[models.Resource], template, suffix,
                  step, context) -> None:
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
        self.rm.add_step_eval(execution_id=step.execution_id,
                              evaluation=ResourceEvaluation(status='rca',
                                                            resource=resource,
                                                            reason=rca,
                                                            remediation=''))

  def add_skipped(self, resource: Optional[models.Resource], reason: str,
                  step_execution_id: str) -> None:
    self.output.print_skipped(resource=resource, reason=reason)
    self.rm.add_step_eval(execution_id=step_execution_id,
                          evaluation=ResourceEvaluation(status='skipped',
                                                        resource=resource,
                                                        reason=reason,
                                                        remediation=''))

  def add_ok(self,
             resource: models.Resource,
             step_execution_id: str,
             reason: str = '') -> None:
    self.output.print_ok(resource=resource, reason=reason)
    self.rm.add_step_eval(execution_id=step_execution_id,
                          evaluation=ResourceEvaluation(status='ok',
                                                        resource=resource,
                                                        reason=reason,
                                                        remediation=''))

  def add_failed(self,
                 resource: models.Resource,
                 reason: str,
                 remediation: str,
                 step_execution_id: str,
                 human_task_msg: str = '') -> Any:
    """Output test result and registers the result to be used in
    the runbook report.

    The failure assigned a human task unless program is running
    autonomously
    """
    self.output.print_failed(resource=resource,
                             reason=reason,
                             remediation=remediation)
    result = ResourceEvaluation(status='failed',
                                resource=resource,
                                reason=reason,
                                remediation=remediation)
    # Add results to report manager so other dependent features can act on it.
    self.rm.add_step_eval(execution_id=step_execution_id, evaluation=result)
    # assign a human task to be completed
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)
    if not config.get(INTERACTIVE_MODE):
      result.prompt_response = choice

      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice

  def add_uncertain(self,
                    step_execution_id: str,
                    resource: models.Resource,
                    reason: str,
                    remediation: str = None,
                    human_task_msg: str = '') -> Any:
    self.output.print_uncertain(reason=reason,
                                resource=resource,
                                remediation=remediation)
    result = ResourceEvaluation(status='uncertain',
                                resource=resource,
                                reason=reason,
                                remediation=remediation)
    self.rm.add_step_eval(execution_id=step_execution_id, evaluation=result)
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)

    if not config.get(INTERACTIVE_MODE):
      result.prompt_response = choice
      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice
