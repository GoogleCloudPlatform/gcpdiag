---
title: "composer/Scheduler Liveness Probe Check"
linkTitle: "Scheduler Liveness Probe Check"
weight: 3
type: docs
description: >
  Check the liveness probe logs for the scheduler via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the liveness probe logs for the scheduler to determine if
  the scheduler is healthy.

### Failure Reason

Liveness probe logs failed found in Cluster.

### Failure Remediation

Running the following checks.
- Check the scheduler CPU utilization.
- Check the scheduler exceeded runs.

### Success Reason

No Liveness probe failed logs found in Cluster.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
