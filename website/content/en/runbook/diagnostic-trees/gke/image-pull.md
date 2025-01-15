---
title: "gke/Image Pull"
linkTitle: "gke/image-pull"
weight: 3
type: docs
description: >
  Analysis and Resolution of Image Pull Failures on GKE clusters.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook investigates the gke cluster for Image pull failures and recommends remediation
  steps.

  Areas Examined:

  - GKE cluster

  - Stackdriver logs

### Executing this runbook

```shell
gcpdiag runbook gke/image-pull \
  -p project_id=value \
  -p name=value \
  -p location=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `name` | False | None | str | (Optional) The name of the GKE cluster, to limit search only for this cluster |
| `location` | False | None | str | (Optional) The zone or region of the GKE cluster |
| `start_time_utc` | False | None | datetime | (Optional) The start window to query the logs. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time_utc` | False | None | datetime | (Optional) The end window for the logs. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Image Pull Start](/runbook/steps/gke/image-pull-start)

  - [Image Not Found](/runbook/steps/gke/image-not-found)

  - [Image Forbidden](/runbook/steps/gke/image-forbidden)

  - [Image Dns Issue](/runbook/steps/gke/image-dns-issue)

  - [Image Connection Timeout Restricted Private](/runbook/steps/gke/image-connection-timeout-restricted-private)

  - [Image Connection Timeout](/runbook/steps/gke/image-connection-timeout)

  - [Image Not Found Insufficient Scope](/runbook/steps/gke/image-not-found-insufficient-scope)

  - [Image Pull End](/runbook/steps/gke/image-pull-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
