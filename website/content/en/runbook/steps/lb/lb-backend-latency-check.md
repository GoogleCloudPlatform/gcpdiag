---
title: "lb/Lb Backend Latency Check"
linkTitle: "Lb Backend Latency Check"
weight: 3
type: docs
description: >
  Check if backend latency exceeds the threshold
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The forwarding rule has a backend latency of {average_latency} ms. This is higher than the threshold value of {threshold} ms.

### Failure Remediation

Investigate the increased backend latency. Check the health and performance of your backend instances, including CPU usage, memory usage, and disk I/O.

### Success Reason

The forwarding rule has a backend latency of {average_latency} ms. This is less than the threshold value of {threshold} ms.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
