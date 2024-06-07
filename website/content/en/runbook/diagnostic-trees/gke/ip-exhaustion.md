---
title: "gke/Ip Exhaustion"
linkTitle: "gke/ip-exhaustion"
weight: 3
type: docs
description: >
  Troubleshooting ip exhaustion issues on GKE clusters.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook investigates the gke cluster for ip exhaustion issues and recommends remediation
  steps.

  Areas Examined:

  - GKE cluster type.

  - GKE cluster and nodepool configuration

  - Stackdriver logs

### Executing this runbook

```shell
gcpdiag runbook gke/ip-exhaustion \
  -p project_id=value \
  -p name=value \
  -p location=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `name` | True | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `location` | True | None | str | The zone or region of the GKE cluster |
| `start_time_utc` | False | None | datetime | The start window to investigate the ip exhaustion. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time_utc` | False | None | datetime | The end window to investigate the ip exhaustion. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Ip Exhaustion Start](/runbook/steps/gke/ip-exhaustion-start)

  - [Ip Exhaustion Gateway](/runbook/steps/gke/ip-exhaustion-gateway)

  - [Node Ip Range Exhaustion](/runbook/steps/gke/node-ip-range-exhaustion)

  - [Pod Ip Range Exhaustion](/runbook/steps/gke/pod-ip-range-exhaustion)

  - [Ip Exhaustion End](/runbook/steps/gke/ip-exhaustion-end)

  - [Ip Exhaustion End](/runbook/steps/gke/ip-exhaustion-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
