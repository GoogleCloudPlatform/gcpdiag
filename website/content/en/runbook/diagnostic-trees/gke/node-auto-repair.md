---
title: "gke/Node Auto Repair"
linkTitle: "gke/node-auto-repair"
weight: 3
type: docs
description: >
  Provides the reason why a Node was auto-repaired
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook checks if:
  - Node auto-repair is enabled on the cluster
  - Nodes was repaired because it was in NotReady status for more than 10 minutes
  - Nodes was repaired because it had disk pressure
  - Nodes was repaired because of unallocatable GPUs
  - Nodes was repaired because of unallocatable TPUs

### Executing this runbook

```shell
gcpdiag runbook gke/node-auto-repair \
  -p project_id=value \
  -p name=value \
  -p gke_cluster_name=value \
  -p node=value \
  -p location=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GKE Cluster |
| `name` | False | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `gke_cluster_name` | False | None | str | The name of the GKE cluster, to limit search only for this cluster |
| `node` | True | None | str | The node name with issues. |
| `location` | False | None | str | The zone or region of the GKE cluster |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Node Auto Repair Start](/runbook/steps/gke/node-auto-repair-start)

  - [Node Not Ready](/runbook/steps/gke/node-not-ready)

  - [Node Disk Full](/runbook/steps/gke/node-disk-full)

  - [Unallocatable Gpu](/runbook/steps/gke/unallocatable-gpu)

  - [Unallocatable Tpu](/runbook/steps/gke/unallocatable-tpu)

  - [Node Auto Repair End](/runbook/steps/gke/node-auto-repair-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
