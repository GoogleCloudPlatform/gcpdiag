---
title: "gke/Ca Pod Not Enough Pdb"
linkTitle: "Ca Pod Not Enough Pdb"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.not.enough.pdb" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed the pod doesn't have enough PodDisruptionBudget.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

Review the PodDisruptionBudget for the Pod and consider making it less restrictive.
To learn more, see
https://cloud.google.com/kubernetes-engine/docs/troubleshooting/cluster-autoscaler-scale-down#not-enough-pdb

### Success Reason

No "no.scale.down.node.pod.not.enough.pdb" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
