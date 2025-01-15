---
title: "gke/Node Unavailability"
linkTitle: "gke/node-unavailability"
weight: 3
type: docs
description: >
  Identifies the reasons for a GKE node being unavailable.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook investigates various factors that may have caused a node to become unavailable,
  including:

  - Live Migration
  - Preemption
  - Removal by the Cluster Autoscaler
  - Node Pool Upgrade

### Executing this runbook

```shell
gcpdiag runbook gke/node-unavailability \
  -p project_id=value \
  -p name=value \
  -p node=value \
  -p location=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `name` | False | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `node` | True | None | str | The node name that was started. |
| `location` | False | None | str | The zone or region of the GKE cluster |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Node Unavailability Start](/runbook/steps/gke/node-unavailability-start)

  - [Live Migration](/runbook/steps/gke/live-migration)

  - [Preemption Condition](/runbook/steps/gke/preemption-condition)

  - [Node Removed By Autoscaler](/runbook/steps/gke/node-removed-by-autoscaler)

  - [Node Pool Upgrade](/runbook/steps/gke/node-pool-upgrade)

  - [Node Unavailability End](/runbook/steps/gke/node-unavailability-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
