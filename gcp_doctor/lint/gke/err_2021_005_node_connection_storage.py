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
from gcp_doctor.queries import gke, logs

MATCH_STR = 'Failed to connect to storage.googleapis.com'
logs_by_project = dict()


def prepare_rule(context: models.Context):
  global logs_by_project
  clusters = gke.get_clusters(context)
  for project_id in {c.project_id for c in clusters.values()}:
    logs_by_project[project_id] = logs.query(
        project_id=project_id,
        resource_type='gce_instance',
        log_name='log_id("serialconsole.googleapis.com/serial_port_1_output")',
        filter_str=f'textPayload:"{MATCH_STR}"')


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  # Any work to do?
  clusters = gke.get_clusters(context)
  if not clusters:
    report.add_skipped(None, 'no clusters found')

  # Search the logs.
  def filter_f(log_entry):
    try:
      return MATCH_STR in log_entry['textPayload']
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
