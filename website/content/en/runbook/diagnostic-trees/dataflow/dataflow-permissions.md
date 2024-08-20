---
title: "dataflow/Dataflow Permissions"
linkTitle: "dataflow/dataflow-permissions"
weight: 3
type: docs
description: >
  Analysis and Resolution of Dataflow Permissions issues.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)
**Kind**: Debugging Tree

### Description

This  runbook investigates Dataflow permissions and recommends remediation steps.

  Areas Examined:
  1. Dataflow user account permissions
  2. Dataflow Service Account
  3. Dataflow Worker Service Account
  4. Dataflow Resource Permissions

### Executing this runbook

```shell
gcpdiag runbook dataflow/dataflow-permissions \
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
| `worker_service_account` | True | None | str | Dataflow Service Account used for Dataflow Job Creation and execution |
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
