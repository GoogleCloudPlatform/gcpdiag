---
title: "composer/Disabled Environment Service Account"
linkTitle: "Disabled Environment Service Account"
weight: 3
type: docs
description: >
  Check the disabled/deleted environment service account via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the disabled/deleted environment service account via Cloud
  Logging.

### Failure Reason

Environment service account is disabled.

### Failure Remediation

If the SA was disabled, re-enable the service account in the
IAM console. Then add a dummy environment variable to the environment's
Environment Variables (e.g. "restart=dummy") or Contact Google Cloud Support.

### Success Reason

Environment service account is not disabled.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
