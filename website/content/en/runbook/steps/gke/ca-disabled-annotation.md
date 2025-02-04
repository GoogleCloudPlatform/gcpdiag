---
title: "gke/Ca Disabled Annotation"
linkTitle: "Ca Disabled Annotation"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.scale.down.disabled.annotation" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because the node is annotated with cluster-autoscaler.kubernetes.io/scale-down-disabled:
true.
Example log entry that would help identify involved objects:
{log_entry}

### Failure Remediation

Cluster autoscaler skips nodes with this annotation without considering their utilization and this message is logged
regardless of the node's utilization factor.
If you want cluster autoscaler to scale down these nodes, remove the annotation.

### Success Reason

No "no.scale.down.node.scale.down.disabled.annotation" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
