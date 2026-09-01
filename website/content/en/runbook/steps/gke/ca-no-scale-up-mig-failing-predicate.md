---
title: "gke/Ca No Scale Up Mig Failing Predicate"
linkTitle: "Ca No Scale Up Mig Failing Predicate"
weight: 3
type: docs
description: >
  Check for "no.scale.up.mig.failing.predicate" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event failed because pending pods could not be scheduled on any potential node pools due to scheduling constraints (predicate failures).
Details of blocking workloads:
{blocking_details}

### Failure Remediation

Examine the predicate failures listed above.
- If pods have 'untolerated taints', make sure your pods tolerate those taints or route them to a pool without those taints.
- If 'Insufficient memory/cpu' is shown, verify if the pod requests exceed the capacity of the node pool's machine type, or if other limits prevent scheduling.
For more information, see: <https://cloud.google.com/kubernetes-engine/docs/troubleshooting/cluster-autoscaler-scale-up#pod-configurations>

### Success Reason

No "no.scale.up.mig.failing.predicate" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
