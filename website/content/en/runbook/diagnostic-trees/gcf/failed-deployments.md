---
title: "gcf/Failed Deployments"
linkTitle: "gcf/failed-deployments"
weight: 3
type: docs
description: >
  Cloud Run function failed deployments check
---

**Product**: [Cloud Functions](https://cloud.google.com/functions)
**Kind**: Debugging Tree

### Description

This runbook will assist users to check reasons for failed deployments of Gen2 cloud functions.
  Current basic Validations:
  - Check for existence of Default SA
  - Check for existence of Cloud function Service Agent
  - Check for existence of cloud functions Service Agent and its permissions
  - Check for error logs for global scope code errors and resource location constraint.

### Executing this runbook

```shell
gcpdiag runbook gcf/failed-deployments \
  -p project_id=value \
  -p name=value \
  -p region=value \
  -p start_time=value \
  -p end_time=value \
  -p gac_service_account=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID containing the cloud function |
| `name` | True | None | str | Name of the cloud function failing deployment |
| `region` | True | None | str | Region of the cloud function failing deployment |
| `start_time` | False | None | datetime | Start time of the issue Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | End time of the issue. Format: YYYY-MM-DDTHH:MM:SSZ |
| `gac_service_account` | False | None | str | Service account used by the user for delpoyment. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Failed Deployments Start](/runbook/steps/gcf/failed-deployments-start)

  - [Default Service Account Check](/runbook/steps/gcf/default-service-account-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [User Service Account Check](/runbook/steps/gcf/user-service-account-check)

  - [Function Global Scope Check](/runbook/steps/gcf/function-global-scope-check)

  - [Location Constraint Check](/runbook/steps/gcf/location-constraint-check)

  - [Failed Deployment End Step](/runbook/steps/gcf/failed-deployment-end-step)


<!--
This file is auto-generated. DO NOT EDIT.
-->
