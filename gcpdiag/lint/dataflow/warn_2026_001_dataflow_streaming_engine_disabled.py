#
# Copyright 2026 Google LLC
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

# Lint as: python3
"""Active Dataflow streaming jobs have Streaming Engine enabled.

Streaming Engine offloads windowing, state management, and other resource-intensive
operations from the worker VMs, improving performance, stability, and autoscaling.
"""

from gcpdiag import lint, models
from gcpdiag.queries import apis, crm, dataflow


def prefetch_rule(context: models.Context):
  """Prefetch jobs and detailed job configurations in background threads."""
  if apis.is_enabled(context.project_id, 'dataflow'):
    jobs = dataflow.get_all_dataflow_jobs(context)
    if not jobs:
      return
    for job in jobs:
      if job.job_type == 'JOB_TYPE_STREAMING' and job.state == 'JOB_STATE_RUNNING':
        dataflow.get_job(project_id=context.project_id, job=job.id, region=job.location)


def run_rule(context: models.Context, report: lint.LintReportRuleInterface):
  project = crm.get_project(context.project_id)

  if not apis.is_enabled(context.project_id, 'dataflow'):
    report.add_skipped(project, 'dataflow api is disabled')
    return

  jobs = dataflow.get_all_dataflow_jobs(context)

  if not jobs:
    report.add_skipped(project, 'no jobs found')
    return

  failed_jobs = set()

  for job in jobs:
    if job.job_type == 'JOB_TYPE_STREAMING' and job.state == 'JOB_STATE_RUNNING':
      full_job = dataflow.get_job(project_id=context.project_id, job=job.id, region=job.location)
      if full_job and not full_job.is_streaming_engine_enabled:
        failed_jobs.add(job.id)

  if failed_jobs:
    report.add_failed(
      project,
      (
        'The following active streaming Dataflow jobs are running without'
        ' Streaming Engine enabled: '
      )
      + ', '.join(sorted(failed_jobs)[:20]),
    )
  else:
    report.add_ok(project)
