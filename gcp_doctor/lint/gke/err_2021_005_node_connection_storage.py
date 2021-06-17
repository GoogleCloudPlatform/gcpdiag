# Lint as: python3
"""GKE nodes aren't reporting connection issues to storage.google.com.

GKE node need to download artifacts from storage.google.com:443 when
booting. If a node reports that it can't connect to storage.google.com,
it probably means that it can't boot correctly.

The following log line is searched in the GCE serial logs: "Failed to connect to
storage.googleapis.com"
"""

from gcp_doctor import lint, models
from gcp_doctor.lint.gke import util

FILTER_STR = 'Failed to connect to storage.googleapis.com'
logs_by_project: dict


def prepare_rule(context: models.Context):
  global logs_by_project
  logs_by_project = util.gke_logs_query(
      context,
      resource_type='gce_instance',
      log_name=
      'projects/{{project_id}}/logs/serialconsole.googleapis.com%2Fserial_port_1_output',
      filter_str=f'textPayload:"{FILTER_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Note: filter_str above is not enough, because logs.query() doesn't guarantee
  # that only matching log lines will be returned. filter_str is only used to
  # restrict the number of transfered logs, but since multiple queries are
  # combined, we need to filter out what isn't "ours".
  def filter_f(log_entry):
    return 'textPayload' in log_entry and FILTER_STR in log_entry['textPayload']

  util.gke_logs_find_bad_nodes(context=context,
                               report=report,
                               logs_by_project=logs_by_project,
                               filter_f=filter_f,
                               failure_message='Connectivity issues detected')
