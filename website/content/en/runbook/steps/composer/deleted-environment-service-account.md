---
title: "composer/Deleted Environment Service Account"
linkTitle: "Deleted Environment Service Account"
weight: 3
type: docs
description: >
  Checks the deleted environment service account via Cloud Logging.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step checks the deleted environment service account via Cloud Logging.

### Failure Reason

Environment service account is deleted.

### Failure Remediation

If the SA was deleted and deletion occurred within the past 30 days,
follow the instructions in [link](https://docs.cloud.google.com/iam/docs/service-accounts-delete-undelete#undeleting)
to undelete the SA.

### Success Reason

Environment service account is not deleted.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
