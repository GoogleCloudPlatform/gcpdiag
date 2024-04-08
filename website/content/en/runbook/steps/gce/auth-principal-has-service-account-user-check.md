---
title: "gce/Auth Principal Has Service Account User Check"
linkTitle: "Auth Principal Has Service Account User Check"
weight: 3
type: docs
description: >
  Verifies if the user has the 'Service Account User' role for a VM's attached service account.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step is crucial for scenarios where a VM utilizes a service account for various operations.
  It ensures the user performing the diagnostics has adequate permissions to use the service account
  attached to the specified VM. Note: This check focuses on project-level roles and does not account
  for permissions inherited from higher-level resources such as folders or organizations.

### Failure Reason

"{auth_user}" does not have the "{sa_user_role}" role or custom roles which has the
constituent permissions required to be able to impersonate the service account "{service_account}".

### Failure Remediation

Assign the "{sa_user_role}" role to "{auth_user}".
Guidelines:
https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#configure_users
https://cloud.google.com/iam/docs/manage-access-service-accounts#grant-single-role

### Success Reason

"{auth_user}" has the "{sa_user_role}"
required to impersonate the service account {service_account}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
