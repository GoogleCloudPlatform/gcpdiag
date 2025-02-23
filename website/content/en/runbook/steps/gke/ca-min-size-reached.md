---
title: "gke/Ca Min Size Reached"
linkTitle: "Ca Min Size Reached"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.node.group.min.size.reached" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Node cannot be removed because its node group is already at its minimum size.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Review and adjust the minimum value set for node pool autoscaling.
https://cloud.google.com/kubernetes-engine/docs/how-to/cluster-autoscaler#resizing_a_node_pool

### Success Reason

No "no.scale.down.node.node.group.min.size.reached" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
