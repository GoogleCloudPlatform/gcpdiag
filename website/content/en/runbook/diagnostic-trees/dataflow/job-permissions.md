---
title: "dataflow/Job Permissions"
linkTitle: "dataflow/job-permissions"
weight: 3
type: docs
description: >
  Analysis and Resolution of Dataflow Jobs Permissions issues.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)
**Kind**: Debugging Tree

### Description

This runbook investigates Dataflow permissions and recommends remediation steps.

  Areas Examined:
  - Dataflow User Account Permissions: Verify that individual Dataflow users have the necessary
    permissions to access and manage Dataflow jobs (e.g., create,update,cancel).

  - Dataflow Service Account Permissions: Verify that the Dataflow Service Account has the required
    permissions to execute and manage the Dataflow jobs

  - Dataflow Worker Service Account: Verify that the Dataflow Worker Service Account has the
    necessary permissions for worker instances within a Dataflow job to access input and
    output resources during job execution.

  - Dataflow Resource Permissions: Verify that Dataflow resources (e.g., Cloud Storage buckets,
    BigQuery datasets) have the necessary permissions to be accessed and used by Dataflow jobs.

  By ensuring that Dataflow resources have the necessary permissions, you
  can prevent errors and ensure that your jobs run smoothly.

### Executing this runbook

```shell
gcpdiag runbook dataflow/job-permissions \
  -p project_id=value \
  -p principal=value \
  -p worker_service_account=value \
  -p cross_project_id=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `principal` | True | None | str | The authenticated user account email. This is the user account that is used to authenticate the user to the console or the gcloud CLI. |
| `worker_service_account` | True | None | str | Dataflow Worker Service Account used for Dataflow Job Creationand execution |
| `cross_project_id` | False | None | str | Cross Project ID, where service account is located if it is not in the same project as the Dataflow Job |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Start Step](/runbook/steps/gcpdiag/start-step)

  - [Dataflow User Account Permissions](/runbook/steps/dataflow/dataflow-user-account-permissions)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Dataflow Worker Service Account Permissions](/runbook/steps/dataflow/dataflow-worker-service-account-permissions)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Org Policy Check](/runbook/steps/crm/org-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Dataflow Resource Permissions](/runbook/steps/dataflow/dataflow-resource-permissions)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Dataflow Permissions End](/runbook/steps/dataflow/dataflow-permissions-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
