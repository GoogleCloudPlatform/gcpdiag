---
title: "composer/Check Auth"
linkTitle: "Check Auth"
weight: 3
type: docs
description: >
  Check for Redis authentication failures.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Detected Redis authentication errors. Check if REDIS_USER or REDIS_PASSWORD are being used in environment variables.

### Failure Remediation

Remove the REDIS_USER and REDIS_PASSWORD environment variable overrides from the Composer environment settings, if set. These variables must remain at their
default values or contact Google Cloud Support.

### Success Reason

No Redis authentication failures detected in logs.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
