---
title: "gke/Ca No Place To Move Pods"
linkTitle: "Ca No Place To Move Pods"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.no.place.to.move.pods" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because there's no place to move Pods.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

If you expect that the Pod should be rescheduled, review the scheduling requirements of the Pods on the underutilized
node to determine if they can be moved to another node in the cluster.
To learn more, see the link
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting/cluster-autoscaler-scale-down#no-place-to-move-pods>

### Success Reason

No "no.scale.down.node.no.place.to.move.pods" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
