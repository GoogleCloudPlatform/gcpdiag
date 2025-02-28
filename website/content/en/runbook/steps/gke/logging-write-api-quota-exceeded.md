---
title: "gke/Logging Write Api Quota Exceeded"
linkTitle: "Logging Write Api Quota Exceeded"
weight: 3
type: docs
description: >
  Verifies that Cloud Logging API write quotas have not been exceeded.
---

**Product**: [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)\
**Step Type**: AUTOMATED STEP

### Description

Checks if the project has exceeded any Cloud Logging write quotas within
  the defined timeframe. Exceeding the quota could prevent nodes from sending
  log data, even if other configurations are correct.

### Failure Reason

The logging health check failed because your project has exceeded its Cloud Logging Write API quota.

### Failure Remediation

Review your logging usage and either reduce log volume or request a quota increase. See instructions:
<https://cloud.google.com/kubernetes-engine/docs/troubleshooting/logging#verify_that_write_api_quotas_have_not_been_reached>

### Success Reason

The project is within its Cloud Logging Write API quota between {start_time} and {end_time}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
