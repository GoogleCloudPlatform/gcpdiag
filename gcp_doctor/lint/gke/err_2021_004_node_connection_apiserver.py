# Lint as: python3
"""GKE nodes aren't reporting connection issues to apiserver.

GKE nodes need to connect to the control plane to register and to report status
regularly. If connection errors are found in the logs, possibly there is a
connectivity issue, like a firewall rule blocking access.

The following log line is searched: "Failed to connect to apiserver"
"""

from gcp_doctor import lint, models
from gcp_doctor.lint.gke import util
from gcp_doctor.queries import gke

MATCH_STR = 'Failed to connect to apiserver'
logs_by_project: dict


def prepare_rule(context: models.Context):
  global logs_by_project
  logs_by_project = util.gke_logs_query(
      context,
      resource_type='k8s_node',
      log_name='projects/{{project_id}}/logs/kubelet',
      filter_str='jsonPayload.MESSAGE:"bootstrap.go" AND ' + \
          f'jsonPayload.MESSAGE:"{MATCH_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Search the logs.
  def filter_f(log_entry):
    try:
      return MATCH_STR in log_entry['jsonPayload']['MESSAGE']
    except KeyError:
      return False

  bad_nodes_by_cluster = util.gke_logs_find_bad_nodes(
      context=context, logs_by_project=logs_by_project, filter_f=filter_f)

  # Create the report.
  for _, c in sorted(clusters.items()):
    if c in bad_nodes_by_cluster:
      report.add_failed(
          c, 'Connectivity issues detected. Nodes:\n. ' +
          '\n. '.join(bad_nodes_by_cluster[c]))
    else:
      report.add_ok(c)
