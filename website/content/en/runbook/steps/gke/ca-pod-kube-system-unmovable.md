---
title: "gke/Ca Pod Kube System Unmovable"
linkTitle: "Ca Pod Kube System Unmovable"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.kube.system.unmovable" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because the pod is a non-DaemonSet, non-mirrored, Pod without a PodDisruptionBudget in the
kube-system namespace.
Example log entry that would help identify involved objects:

{log_entry}

### Failure Remediation

By default, Pods in the kube-system namespace aren't removed by cluster autoscaler.

To resolve this issue, either add a PodDisruptionBudget for the kube-system Pods or use a combination of node pools
taints and tolerations to separate kube-system Pods from your application Pods.
To learn more, see
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting/cluster-autoscaler-scale-down#kube-system-unmoveable>

### Success Reason

No "no.scale.down.node.pod.kube.system.unmovable" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
