---
title: "composer/Check Ephemeral Storage"
linkTitle: "Check Ephemeral Storage"
weight: 3
type: docs
description: >
  Check for worker pod evictions due to ephemeral storage exhaustion.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This check verifies if there are any worker pod evictions due to ephemeral
  storage exhaustion.

### Failure Reason

Ephemeral Storage Exhaustion found in Logs.

### Failure Remediation

Follow documentation : <https://docs.cloud.google.com/composer/docs/composer-2/troubleshooting-dags#task-fails-pod-eviction>

### Success Reason

No Ephemeral Storage Exhaustion found in Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
