# Lint as: python3
"""

This module contains linting rules to confirm all Looker
(Google Cloud core) instance operations are inventoried
"""

from gcpdiag import lint, models
from gcpdiag.queries import looker


def format_operation_message(operation):
  """Helper function to format the operation message."""
  create_time_str = operation.create_time.strftime(
      '%Y-%m-%d %H:%M:%S') if operation.create_time else 'N/A'

  if operation.status == 'In Progress':
    action_message = (
        f'Activity: {operation.operation_type}'
        f'Started: {create_time_str} | Status: {operation.status}.')

  else:
    action_message = (
        f'Activity: {operation.operation_type} | Action: {operation.action}'
        f'Started: {create_time_str} | Status: {operation.status}.')

  return (f'\n  Location: {operation.location_id}\n'
          f'  Instance: {operation.instance_name}\n'
          f'    - {action_message}')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  operations_by_location = looker.get_operations(context)

  if not operations_by_location:
    report.add_skipped(None, 'No operations found')
    return

  for _, instances in operations_by_location.items():
    for _, operations in instances.items():
      for operation in operations:
        message = format_operation_message(operation)
        if operation.status == 'In Progress':
          report.add_failed(operation, message)
        else:
          report.add_ok(operation, message)
