---
title: "gke/Node Removed By Autoscaler"
linkTitle: "Node Removed By Autoscaler"
weight: 3
type: docs
description: >
  Checks if the node was removed by Cluster Autoscaler.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {NODE} was removed by the cluster autoscaler.

### Failure Remediation

This is expected behavior. GKE's cluster autoscaler automatically resizes the number of nodes in a given node pool, based on the demands of your workloads. When demand is low, the cluster autoscaler scales back down to a minimum size that you designate.

For more details about Cluster Autoscaler ScaleDown events please consult the documentation:
https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-autoscaler-visibility#scaledown-event

### Success Reason

The node {NODE} was unavailable for reasons other than scale down by the cluster autoscaler.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
