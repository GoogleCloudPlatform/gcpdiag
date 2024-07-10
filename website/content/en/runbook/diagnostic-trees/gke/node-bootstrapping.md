---
title: "gke/Node Bootstrapping"
linkTitle: "gke/node-bootstrapping"
weight: 3
type: docs
description: >
  Analyses issues experienced when adding nodes to your GKE Standard cluster.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)
**Kind**: Debugging Tree

### Description

This runbook requires at least
  - location and node parameters. Location here is the zone where the node is running,
  for example us-central1-c.
  - location, nodepool and cluster name parameters to be provided. Location is zone or region for
  a nodepool, if the cluster is a regional cluster, then location for a nodepool will be the
  cluster region. For example a region could be us-central1.

  If a location/node pair is provided, the runbook will check the Node Registration Checker output
  for the given location/node pair.

  If a location, nodepool and GKE cluster name parameters are provided, the runbook will check for
  any errors that might have occurred when the instances.insert method was invoked for the given
  parameters.

### Executing this runbook

```shell
gcpdiag runbook gke/node-bootstrapping \
  -p location=value \
  -p node=value \
  -p nodepool=value \
  -p name=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `location` | True | None | str | The location where the node or nodepool is. For a node, location will be the zone where the node is running (i.e. us-central1-c). For a nodepool, this can be the zone or the region (i.e. us-central1) where the nodepool is configured |
| `node` | False | None | str | The node name that is failing to register (if available). If node name is not available, please provide the nodepool name where nodes aren't registering |
| `nodepool` | False | None | str | The nodepool name where nodes aren't registering, if a node name is not availalbe |
| `name` | False | None | str | The GKE cluster name. When providing nodepool name, please provide the GKE cluster name as well to be able to properly filter events in the logging query. |
| `start_time_utc` | False | None | datetime | The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time_utc` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Node Bootstrapping Start](/runbook/steps/gke/node-bootstrapping-start)

  - [Node Insert Check](/runbook/steps/gke/node-insert-check)

  - [Node Registration Success](/runbook/steps/gke/node-registration-success)

  - [Node Bootstrapping End](/runbook/steps/gke/node-bootstrapping-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
