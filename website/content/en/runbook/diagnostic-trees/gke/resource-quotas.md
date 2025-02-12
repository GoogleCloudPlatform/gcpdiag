---
title: "gke/Resource Quotas"
linkTitle: "gke/resource-quotas"
weight: 3
type: docs
description: >
  Analyses logs in the project where the cluster is running.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

If there are log entries that contain messages listed in the public documentation
  https://cloud.google.com/knowledge/kb/google-kubernetes-engine-pods-fail-to-start-due-to-exceeded-quota-000004701
  then provide details on how this issue can be solved.

### Executing this runbook

```shell
gcpdiag runbook gke/resource-quotas \
  -p project_id=value \
  -p name=value \
  -p location=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `name` | True | None | str | (Optional) The name of the GKE cluster, to limit search only for this cluster |
| `location` | True | None | str | (Optional) The zone or region of the GKE cluster |
| `start_time` | False | None | datetime | (Optional) The start window to query the logs. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | (Optional) The end window for the logs. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Resource Quotas Start](/runbook/steps/gke/resource-quotas-start)

  - [Service Api Status Check](/runbook/steps/gcp/service-api-status-check)

  - [Cluster Version](/runbook/steps/gke/cluster-version)

  - [Resource Quota Exceeded](/runbook/steps/gke/resource-quota-exceeded)

  - [Resource Quotas End](/runbook/steps/gke/resource-quotas-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
