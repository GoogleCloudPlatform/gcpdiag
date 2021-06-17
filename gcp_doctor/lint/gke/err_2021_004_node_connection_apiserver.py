# Lint as: python3
"""GKE nodes aren't reporting connection issues to apiserver.

GKE nodes need to connect to the control plane to register and to report status
regularly. If connection errors are found in the logs, possibly there is a
connectivity issue, like a firewall rule blocking access.

The following log line is searched: "Failed to connect to apiserver"
"""

from gcp_doctor import lint, models
from gcp_doctor.lint.gke import util

logs_by_project: dict


def prepare_rule(context: models.Context):
  global logs_by_project
  logs_by_project = util.gke_logs_query(
      context,
      resource_type='k8s_node',
      log_name='projects/{{project_id}}/logs/kubelet',
      filter_str='jsonPayload.MESSAGE:"bootstrap.go" AND ' +
      'jsonPayload.MESSAGE:"Failed to connect to apiserver"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Note: filter_str above is not enough, because logs.query() doesn't guarantee
  # that only matching log lines will be returned. filter_str is only used to
  # restrict the number of transfered logs, but since multiple queries are
  # combined, we need to filter out what isn't "ours".
  def filter_f(log_entry):
    return 'jsonPayload' in log_entry and \
        'MESSAGE' in log_entry['jsonPayload'] and \
        'bootstrap.go' in log_entry['jsonPayload']['MESSAGE'] and \
        'Failed to connect to apiserver' in log_entry['jsonPayload']['MESSAGE']

  util.gke_logs_find_bad_nodes(context=context,
                               report=report,
                               logs_by_project=logs_by_project,
                               filter_f=filter_f,
                               failure_message='Connectivity issues detected')
