---
title: "gcf/Default Service Account Check"
linkTitle: "Default Service Account Check"
weight: 3
type: docs
description: >
  Check if cloud run function default service account and agent exists and is enabled.
---

**Product**: [Cloud Functions](https://cloud.google.com/functions)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The Cloud Functions service agent or the default runtime service account does not exist or is not enabled:
<https://cloud.google.com/functions/docs/concepts/iam#access_control_for_service_accounts>

### Failure Remediation

Refer to the IAM roles guide for providing default roles to the Cloud Run function default service account and the service agent:
<https://cloud.google.com/functions/docs/concepts/iam#serviceaccount>

### Success Reason

The service agent and default service account exist and are enabled.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
