---
title: "composer/Scheduler Cpu Utilization"
linkTitle: "Scheduler Cpu Utilization"
weight: 3
type: docs
description: >
  Check the scheduler CPU utilization via Monitoring.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the scheduler CPU utilization to determine if the scheduler
  is overloaded.

### Failure Reason

Scheduler CPU utilization above the threshold.

### Failure Remediation

Increase the number of schedulers or the CPUs allocated to the scheduler.

### Success Reason

Scheduler CPU utilization below the threshold.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
