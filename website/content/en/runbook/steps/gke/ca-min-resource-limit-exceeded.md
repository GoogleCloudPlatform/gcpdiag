---
title: "gke/Ca Min Resource Limit Exceeded"
linkTitle: "Ca Min Resource Limit Exceeded"
weight: 3
type: docs
description: >
  Check for "no.scale.down.node.minimal.resource.limits.exceeded" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleDown event failed because  it would violate cluster-wide minimal resource limits.
These are the resource limits set for node auto-provisioning.
Example log entry that would help identify involved objects:
{LOG_ENTRY}

### Failure Remediation

Review your limits for memory and vCPU and, if you want cluster autoscaler to scale down this node, decrease the limits by following the documentation
https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-provisioning#enable

### Success Reason

No "no.scale.down.node.minimal.resource.limits.exceeded" errors found between {START_TIME_UTC} and {END_TIME_UTC} UTC



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
