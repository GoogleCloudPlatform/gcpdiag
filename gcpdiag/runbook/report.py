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
from gcpdiag.runbook.output import terminal_output
from gcpdiag.runbook.output.api_output import ApiOutput
from gcpdiag.runbook.output.base_output import BaseOutput


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
  start_time: str
  end_time: str
  results: List[ResourceEvaluation]
  prompt_response: Any
  metadata: dict
  info: List
  step_error: str

  def __init__(self, step):
    self.execution_id = step.execution_id
    self.step = step
    self.results = []
    self.metadata = OrderedDict()
    self.info = []
    self.prompt_response = None
    self.step_error = None

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
    if self.step_error:
      return 'skipped'
    for status in constants.STATUS_ORDER:
      if self.totals_by_status.get(status):
        return status
    return 'no_status'

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


class Report:
  """Report for a runbook or bundle"""
  # Same as the runbook or bundle run_id
  run_id: str
  runbook_name: Optional[str] = None
  run_start_time: str
  run_end_time: str
  execution_mode: str
  parameters: models.Parameter
  results: Dict[str, StepResult]

  def __init__(self, run_id, parameters) -> None:
    self.run_id = run_id
    self.parameters = parameters
    self.results = {}
    self.execution_mode = 'NON_INTERACTIVE' if config.get(
        'auto') else 'INTERACTIVE'

  @property
  def any_failed(self) -> bool:
    return any(r.overall_status in ('failed', 'uncertain')
               for r in self.results.values())

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = collections.defaultdict(int)
    for step_result in self.results.values():
      totals[step_result.overall_status] += 1
    return totals

  def get_rule_statuses(self) -> Dict[str, str]:
    return {
        str(r.execution_id): r.overall_status for r in self.results.values()
    }


class ReportManager:
  """Base Report Manager subclassed to hand different interfaces (cli, api)"""
  reports: Dict[str, Report] = {}

  def __init__(self) -> None:
    self.reports = {}

  def add_step_result(self, run_id, result: StepResult):
    self.reports[run_id].results[result.execution_id] = result

  def add_step_eval(self, run_id, execution_id, evaluation: ResourceEvaluation):
    self.reports[run_id].results[execution_id].results.append(evaluation)

  def add_step_prompt_response(self, run_id, execution_id, prompt_response):
    self.reports[run_id].results[execution_id].prompt_response = prompt_response

  def serialize_report(self, report: Report):

    def improve_formatting(text):
      if text is None:
        return None
      # Decode escaped sequences like \\n, \\r, \\t to their actual characters
      text = text.encode('utf-8').decode('unicode_escape')
      # Remove extra spaces at start / end of string
      text = text.strip()
      return text

    def resource_evaluation(eval_list: List[ResourceEvaluation]):
      return [{
          'resource':
              r.resource.full_path if r.resource else '-',
          'status':
              r.status,
          'reason':
              improve_formatting(str(r.reason)),
          'remediation':
              improve_formatting(r.remediation)
              if r.remediation else 'No remediation needed',
          'remediation_skipped':
              False if config.get('auto') else r.remediation_skipped
      } for r in eval_list]

    def result_to_dict(entry: StepResult):
      return {
          'execution_id': entry.step.execution_id,
          'totals_by_status': entry.totals_by_status,
          'description': improve_formatting(entry.step.__doc__),
          'name': improve_formatting(entry.step.name) or '',
          'execution_message': improve_formatting(entry.step.name) or '',
          'overall_status': entry.overall_status,
          'start_time': entry.start_time,
          'end_time': entry.end_time,
          'metadata': entry.metadata,
          'info': entry.info,
          'execution_error': entry.step_error,
          'resource_evaluation': resource_evaluation(entry.results)
      }

    def parse_report_data(data):
      if isinstance(data, StepResult):
        return result_to_dict(data)
      else:
        return str(data)

    report_dict = {
        'run_id': report.run_id,
        'execution_mode': report.execution_mode,
        'start_time': report.run_start_time,
        'end_time': report.run_end_time,
        'parameters': report.parameters,
        'totals_by_status': report.get_totals_by_status(),
        'results': report.results
    }

    return json.dumps(report_dict,
                      ensure_ascii=False,
                      default=parse_report_data,
                      indent=2)

  def generate_reports(self):
    raise NotImplementedError

  def get_totals_by_status(self) -> Dict[str, int]:
    totals: Dict[str, int]
    totals = collections.defaultdict(int)
    for report in self.reports.values():
      totals.update(report.get_totals_by_status())
    return totals

  def generate_report_metrics(self, report: Report) -> Dict[str, dict]:
    reports_metrics: Dict[str, Any] = {}
    all_step_metrics = []
    reports_metrics['execution_mode'] = report.execution_mode
    for result in report.results.values():
      step_metrics: Dict[str, dict] = collections.defaultdict(dict)
      start = util.parse_time_input(result.start_time)
      end = util.parse_time_input(result.end_time)
      duration = (end - start).total_seconds() * 1000
      step_metrics[result.step.id]['execution_duration'] = duration
      step_metrics[result.step.id]['totals_by_status'] = result.totals_by_status
      step_metrics[result.step.id]['error'] = bool(result.step_error)
      all_step_metrics.append(step_metrics)
    if report.runbook_name:
      start = util.parse_time_input(report.run_start_time)
      end = util.parse_time_input(report.run_end_time)
      duration = (end - start).total_seconds() * 1000
      reports_metrics['runbook_name'] = report.runbook_name
      reports_metrics['run_duration'] = duration
      reports_metrics['totals_by_status'] = report.get_totals_by_status()
      reports_metrics['steps'] = all_step_metrics
    else:
      reports_metrics['steps'] = all_step_metrics
    return reports_metrics

  def add_step_metadata(self, run_id, key, value, step_execution_id):
    step_result = None
    if step_execution_id:
      step_result = self.reports[run_id].results[step_execution_id]
    if step_result:
      step_result.metadata[key] = value

  def add_step_info_metadata(self, run_id, value, step_execution_id):
    step_result = None
    if step_execution_id:
      step_result = self.reports[run_id].results[step_execution_id]
    if step_result:
      step_result.info.append(value)

  def get_step_metadata(self, run_id, key, step_execution_id):
    step_result = None
    if step_execution_id:
      step_result = self.reports[run_id].results[step_execution_id]
    if step_result:
      return step_result.metadata.get(key)
    return None

  def get_all_step_metadata(self, run_id, step_execution_id) -> dict:
    step_result = None
    if step_execution_id:
      step_result = self.reports[run_id].results[step_execution_id]
    if step_result:
      return step_result.metadata
    return {}


class ApiReportManager(ReportManager):
  """Report Manager for API interactions with runbooks"""

  def generate_reports(self):
    """Generate Runbook Report"""
    reports = []
    for _, report in self.reports.items():
      # TODO: Refactor serialization logic to allow
      # converting a report into a dict without serialization
      reports.append(json.loads(self.serialize_report(report)))
    return reports


class TerminalReportManager(ReportManager):
  """ Class representing results of runbook """

  def get_report_path(self, run_id):
    if os.getenv('MODE') == 'server':
        return "/dev/stdout"
    print("get_report_path " + config + "\n" + config.get('report_dir'))
    date = datetime.now(timezone.utc).strftime('%Y_%m_%d_%H_%M_%S_%Z')
    report_name = f"gcpdiag_runbook_report_{re.sub(r'[.]', '_', run_id)}_{date}.json"
    return os.path.join(config.get('report_dir'), report_name)

  def generate_reports(self):
    """Generate Runbook Report"""
    for run_id, report in self.reports.items():
      result = self.serialize_report(report)
      path = self.get_report_path(run_id)
      self._write_report_to_terminal(path, result)
    return json.loads(result)

  def _write_report_to_terminal(self, out_path, json_report):
    try:
      with open(out_path, 'w', encoding='utf-8') as file:
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

  def __init__(self, kind) -> None:
    if kind == constants.CLI:
      self.rm = TerminalReportManager()
      self.output = terminal_output.TerminalOutput()
    elif kind == constants.API:
      self.rm = ApiReportManager()
      self.output = ApiOutput()
    else:
      raise AttributeError(
          f'No valid interface specified {kind}. specify `cli` or `api`')

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

  def prepare_rca(self, run_id, resource: Optional[models.Resource], template,
                  suffix, step, context) -> None:
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
        self.rm.add_step_eval(run_id=run_id,
                              execution_id=step.execution_id,
                              evaluation=ResourceEvaluation(status='rca',
                                                            resource=resource,
                                                            reason=rca,
                                                            remediation=''))

  def add_skipped(self, run_id, resource: Optional[models.Resource],
                  reason: str, step_execution_id: str) -> None:
    self.output.print_skipped(resource=resource, reason=reason)
    self.rm.add_step_eval(run_id,
                          execution_id=step_execution_id,
                          evaluation=ResourceEvaluation(status='skipped',
                                                        resource=resource,
                                                        reason=reason,
                                                        remediation=''))

  def add_ok(self,
             run_id: str,
             resource: models.Resource,
             step_execution_id: str,
             reason: str = '') -> None:
    self.output.print_ok(resource=resource, reason=reason)
    self.rm.add_step_eval(run_id=run_id,
                          execution_id=step_execution_id,
                          evaluation=ResourceEvaluation(status='ok',
                                                        resource=resource,
                                                        reason=reason,
                                                        remediation=''))

  def add_failed(self,
                 run_id: str,
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
    self.rm.add_step_eval(run_id=run_id,
                          execution_id=step_execution_id,
                          evaluation=result)
    # assign a human task to be completed
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)

    if not config.get(INTERACTIVE_MODE):
      self.rm.add_step_prompt_response(run_id=run_id,
                                       execution_id=step_execution_id,
                                       prompt_response=choice)

      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice

  def add_uncertain(self,
                    run_id: str,
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
    self.rm.add_step_eval(run_id=run_id,
                          execution_id=step_execution_id,
                          evaluation=result)
    choice = self.output.prompt(kind=constants.HUMAN_TASK,
                                message=human_task_msg)

    if not config.get(INTERACTIVE_MODE):
      self.rm.add_step_prompt_response(run_id=run_id,
                                       execution_id=step_execution_id,
                                       prompt_response=choice)
      if choice is constants.CONTINUE or choice is constants.STOP:
        result.remediation_skipped = True
      return choice
