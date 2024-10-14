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

Health check logging is enabled

### Uncertain Reason

Logging is not enabled for health check

### Uncertain Remediation

Enable logging for the health check using the following gcloud command:

gcloud compute health-checks update {protocol} {hc_name} {additional_flags}--enable-logging

This will log any future changes in health status but won't show any past activity. Note that the new health check logs will only appear when a health state transition occurs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->