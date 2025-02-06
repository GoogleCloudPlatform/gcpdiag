---
title: "gke/Ca Ip Space Exhausted"
linkTitle: "Ca Ip Space Exhausted"
weight: 3
type: docs
description: >
  Check for "scale.up.error.ip.space.exhausted" log entries
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The scaleUp event failed because the cluster doesn't have enough unallocated IP address space to use to add new nodes or
Pods.
Example log entry that would help identify involved objects:
{log_entry}

### Failure Remediation

Refer to the troubleshooting steps to address the lack of IP address space for the nodes or pods.
https://cloud.google.com/kubernetes-engine/docs/how-to/alias-ips#not_enough_space

### Success Reason

No "scale.up.error.ip.space.exhausted" errors found between {start_time} and {end_time}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
