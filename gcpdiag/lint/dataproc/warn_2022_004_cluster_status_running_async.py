"""Dataproc cluster is in RUNNING state

Cluster should normally spend most of the time in RUNNING state.
"""

from gcpdiag import lint, models
from gcpdiag.async_queries.project import get_project


async def async_run_rule(context: models.Context,
                         report: lint.LintReportRuleInterface) -> None:
  project = get_project.get_project(project_id=context.project_id)
  cluster_names = await project.dataproc.list_clusters()
  for cluster_name in cluster_names:
    cluster = await project.dataproc.get_cluster_by_name(cluster_name)
    if cluster.status == 'RUNNING':
      report.add_ok(cluster)
    else:
      report.add_failed(cluster, 'cluster is not running')
