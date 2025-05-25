---
title: "gcf/User Service Account Check"
linkTitle: "User Service Account Check"
weight: 3
type: docs
description: >
  Check if User/Service account has permissions on Cloud function runtime service account
---

**Product**: [Cloud Functions](https://cloud.google.com/functions)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The user principal '{user_principal}' does not have roles/iam.serviceAccountUser role on the runtime Service Account '{runtime_account}'

### Failure Remediation

Assign the Service Account User role (roles/iam.serviceAccountUser) to the user on the default or non-default runtime service account.
This role includes the iam.serviceAccounts.actAs permission.
<https://cloud.google.com/functions/docs/reference/iam/roles#additional-configuration>

### Success Reason

The user principal '{user_principal}' has roles/iam.serviceAccountUser role on the runtime Service Account '{runtime_account}'



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
