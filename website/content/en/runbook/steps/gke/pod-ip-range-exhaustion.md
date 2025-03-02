---
title: "gke/Pod Ip Range Exhaustion"
linkTitle: "Pod Ip Range Exhaustion"
weight: 3
type: docs
description: >
  Check Pod IP Range Exhaustion and offer remediation.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Checks Pod IP range exhaustion and offers remediation step.

### Failure Reason

Pod IP exhaustion is detected in the cluster {cluster_name}

### Failure Remediation

Please follow the below documentation [1] to add ipv4 range to the autopilot cluster to mitgate the issue.

[1] <https://cloud.google.com/kubernetes-engine/docs/how-to/multi-pod-cidr#add-pod-ipv4-range-in-autopilot-cluster>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
