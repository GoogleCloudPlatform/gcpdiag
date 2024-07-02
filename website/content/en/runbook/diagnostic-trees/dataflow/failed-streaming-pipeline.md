---
title: "dataflow/Failed Streaming Pipeline"
linkTitle: "dataflow/failed-streaming-pipeline"
weight: 3
type: docs
description: >
  Diagnostic checks for failed Dataflow Streaming Pipelines.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)
**Kind**: Debugging Tree

### Description

Provides a DiagnosticTree to check for issues related to failed streaming
  pipelines.

  - Examples:
    - Pipeline failed to launch
    - Workers not starting

### Executing this runbook

```shell
gcpdiag runbook dataflow/failed-streaming-pipeline \
  -p project_id = value \
  -p job_id = value \
  -p job_region = value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `job_id` | True | None | str | The Job ID returned when the launch command is submitted |
| `job_region` | True | None | str | The region configured for the job |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Failed Streaming Pipeline Start](/runbook/steps/dataflow/failed-streaming-pipeline-start)

  - [Job Is Streaming](/runbook/steps/dataflow/job-is-streaming)

  - [Valid Sdk](/runbook/steps/dataflow/valid-sdk)

  - [Job Graph Is Constructed](/runbook/steps/dataflow/job-graph-is-constructed)

  - [Failed Streaming Pipeline End](/runbook/steps/dataflow/failed-streaming-pipeline-end)

  - [Job Logs Visible](/runbook/steps/dataflow/job-logs-visible)

  - [Failed Streaming Pipeline End](/runbook/steps/dataflow/failed-streaming-pipeline-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
