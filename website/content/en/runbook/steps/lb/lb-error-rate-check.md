---
title: "lb/Lb Error Rate Check"
linkTitle: "Lb Error Rate Check"
weight: 3
type: docs
description: >
  Check if error exceeds the threshold
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The forwarding rule has an average error rate of {average_error_rate}% in the last 15 minutes. This is higher than the threshold value of {threshold}%.

### Failure Remediation

A high error rate indicates potential problems with the backend service. Check the logs for 5xx errors and investigate the root cause. Common issues include application errors and resource exhaustion. If the errors correlate with specific requests, examine those requests for patterns or anomalies.

### Success Reason

The forwarding rule has an average error rate of {average_error_rate}% in the last 15 minutes. This is less than the threshold value of {threshold}%.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
