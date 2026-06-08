---
title: "dataflow/Failed Batch Pipeline"
linkTitle: "dataflow/failed-batch-pipeline"
weight: 3
type: docs
description: >
  Diagnostic checks for failed Dataflow Batch Pipelines.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)
**Kind**: Debugging Tree

### Description

Provides a DiagnosticTree to check for issues related to failed batch
  pipelines.

  - Examples:
    - Pipeline failed to launch
    - Workers failed to start or are crashlooping

### Executing this runbook

```shell
gcpdiag runbook dataflow/failed-batch-pipeline \
  -p project_id=value \
  -p dataflow_job_id=value \
  -p job_region=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `dataflow_job_id` | True | None | str | The Job ID returned when the launch command is submitted |
| `job_region` | True | None | str | The region configured for the job |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Failed Batch Pipeline Start](/runbook/steps/dataflow/failed-batch-pipeline-start)

  - [Job Is Batch](/runbook/steps/dataflow/job-is-batch)

  - [Valid Sdk](/runbook/steps/dataflow/valid-sdk)

  - [Dataflow Quotas](/runbook/steps/dataflow/dataflow-quotas)

  - [Job Graph Is Constructed](/runbook/steps/dataflow/job-graph-is-constructed)

  - [Job Logs Visible](/runbook/steps/dataflow/job-logs-visible)

  - [Batch Failed Job Logs](/runbook/steps/dataflow/batch-failed-job-logs)

  - [Job Log Errors](/runbook/steps/dataflow/job-log-errors)

  - [Slow Job Logs](/runbook/steps/dataflow/slow-job-logs)

  - [Batch Worker Metrics](/runbook/steps/dataflow/batch-worker-metrics)

  - [Failed Batch Pipeline End](/runbook/steps/dataflow/failed-batch-pipeline-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
