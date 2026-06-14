---
title: "bigquery/Failed Query"
linkTitle: "bigquery/failed-query"
weight: 3
type: docs
description: >
  Diagnoses issues with a failed BigQuery query job.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)
**Kind**: Debugging Tree

### Description

This runbook investigates why a specific BigQuery job failed by verifying the
  job's status and analyzing the error message against a set of known issues to
  provide targeted remediation steps.

### Executing this runbook

```shell
gcpdiag runbook bigquery/failed-query \
  -p project_id=value \
  -p bigquery_job_region=value \
  -p bigquery_job_id=value \
  -p bigquery_skip_permission_check=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID where the BigQuery job was run. |
| `bigquery_job_region` | True | None | str | The region where the BigQuery job was run. |
| `bigquery_job_id` | True | None | str | The identifier of the failed BigQuery Job. |
| `bigquery_skip_permission_check` | False | False | bool | Indicates whether to skip the permission check to speed up the investigation. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Big Query Failed Query Start](/runbook/steps/bigquery/big-query-failed-query-start)

  - [Run Permission Checks](/runbook/steps/bigquery/run-permission-checks)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)

  - [Big Query Job Exists](/runbook/steps/bigquery/big-query-job-exists)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)

  - [Confirm Bq Job Is Done](/runbook/steps/bigquery/confirm-bq-job-is-done)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)

  - [Big Query End](/runbook/steps/bigquery/big-query-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
