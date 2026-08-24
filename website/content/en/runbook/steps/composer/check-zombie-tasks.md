---
title: "composer/Check Zombie Tasks"
linkTitle: "Check Zombie Tasks"
weight: 3
type: docs
description: >
  Check for Zombie tasks or SIGKILL signals in environment logs.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This check verifies if there are any Zombie tasks or SIGKILL signals in the
  environment logs.

### Failure Reason

Zombie Tasks found in Logs.

### Failure Remediation

Follow documentation : <https://docs.cloud.google.com/composer/docs/composer-2/troubleshooting-dags#sigterm>

### Success Reason

No Zombie Tasks found in Logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
