---
title: "composer/Service Account Status"
linkTitle: "Service Account Status"
weight: 3
type: docs
description: >
  Check the status of the Composer environment's service accounts.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step queries the IAM API to see if the service accounts associated with
  the Composer environment exist.

### Failure Reason

Service account is missing or disabled.

### Failure Remediation

Verify the service account status in the IAM page. Follow the [documentation](https://docs.cloud.google.com/iam/docs/service-accounts-delete-undelete) for details.

### Success Reason

Service account is active.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
