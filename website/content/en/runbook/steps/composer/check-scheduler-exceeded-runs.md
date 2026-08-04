---
title: "composer/Check Scheduler Exceeded Runs"
linkTitle: "Check Scheduler Exceeded Runs"
weight: 3
type: docs
description: >
  Check the scheduler exceeded 5,000 runs via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the scheduler exceeded 5,000 runs via Cloud Logging.

### Failure Reason

Scheduler exceeded 5,000 runs found in Cluster Logs.

### Failure Remediation

This is a normal operation in Airflow Scheduler.
See <https://docs.cloud.google.com/composer/docs/composer-3/troubleshooting-scheduling#min-file-process-interval> for more details.

### Success Reason

Scheduler exceeded 5,000 runs not found in Cluster Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
