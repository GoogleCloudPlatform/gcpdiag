---
title: "gke/Preemption Condition"
linkTitle: "Preemption Condition"
weight: 3
type: docs
description: >
  Checks if the node was preempted.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The node {NODE} was preempted.

### Failure Remediation

Compute Engine might stop (preempt) preemptible instances if it needs to reclaim the compute capacity for allocation to other VMs.

For more details about preemptible VMs in GKE please consult the documentation:
https://cloud.google.com/kubernetes-engine/docs/how-to/preemptible-vms

### Success Reason

The node {NODE} was unavailable for reasons other than preemption.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
