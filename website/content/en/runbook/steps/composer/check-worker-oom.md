---
title: "composer/Check Worker Oom"
linkTitle: "Check Worker Oom"
weight: 3
type: docs
description: >
  Check for Out-of-Memory (OOM) events in worker pods.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This check verifies if there are any OOMKilled events in the worker pods.

### Failure Reason

OOMKilled events found in Cluster Logs.

### Failure Remediation

Follow documentation : <https://docs.cloud.google.com/composer/docs/composer-2/troubleshooting-dags#task-fails-pod-eviction>

### Success Reason

No OOMKilled Events found in Cluster Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
