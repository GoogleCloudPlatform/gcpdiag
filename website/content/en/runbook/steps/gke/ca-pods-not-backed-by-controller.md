---
title: "gke/Ca Pods Not Backed By Controller"
linkTitle: "Ca Pods Not Backed By Controller"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.pod.not.backed.by.controller" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because a Pod is not backed by a controller such as ReplicationController, DaemonSet, Job,
StatefulSet, or ReplicaSet.
Example log entry that would help identify involved objects:
{log_entry}

### Failure Remediation

Set the annotation "cluster-autoscaler.kubernetes.io/safe-to-evict": "true" for the Pod or define an acceptable
controller

### Success Reason

No "no.scale.down.node.pod.not.backed.by.controller" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
