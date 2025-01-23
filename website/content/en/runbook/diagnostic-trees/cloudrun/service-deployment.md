---
title: "cloudrun/Service Deployment"
linkTitle: "cloudrun/service-deployment"
weight: 3
type: docs
description: >
  Investigates the necessary GCP components searching for reasons for deployment errors.
---

**Product**: [Cloud Run](https://cloud.google.com/run)
**Kind**: Debugging Tree

### Description

This runbook will examine the following key areas:

  1. Container and code Checks.
    - Ensures the Container is in correct state to run in Cloud Run

  Scope of Investigation:
    - Note that this runbook does not provide troubleshooting steps for errors
      caused by the code running in the container.

### Executing this runbook

```shell
gcpdiag runbook cloudrun/service-deployment \
  -p project_id=value \
  -p region=value \
  -p service_name=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `region` | True | None | str | Region of the service. |
| `service_name` | True | None | str | Name of the Cloud Run service |
| `start_time` | False | None | datetime | Start time of the issue |
| `end_time` | False | None | datetime | End time of the issue |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Service Deployment Start](/runbook/steps/cloudrun/service-deployment-start)

  - [Service Deployment Code Step](/runbook/steps/cloudrun/service-deployment-code-step)

  - [Container Failed To Start Step](/runbook/steps/cloudrun/container-failed-to-start-step)

  - [Image Was Not Found Step](/runbook/steps/cloudrun/image-was-not-found-step)

  - [No Permission For Image Step](/runbook/steps/cloudrun/no-permission-for-image-step)


<!--
This file is auto-generated. DO NOT EDIT.
-->
