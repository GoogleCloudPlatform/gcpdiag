---
title: "lb/Verify Health Check Logging Enabled"
linkTitle: "Verify Health Check Logging Enabled"
weight: 3
type: docs
description: >
  Check if health check logging is enabled.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: GATEWAY

### Description

None

### Success Reason

Health check logging is enabled for health check {hc_url}.

### Uncertain Reason

Logging is not enabled for health check {hc_url}, making troubleshooting considerably harder. Without logs, visibility into health check state changes and probe details is lacking, hindering the ability to diagnose the cause of failures.

### Uncertain Remediation

To facilitate troubleshooting, enable logging for the health check using the following `gcloud` command:

```
gcloud compute health-checks update {protocol} {hc_name} {additional_flags} --enable-logging
```

This will log any future changes in health status, but won't show past activity. Note that new health check logs will only appear when a health state transition occurs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
