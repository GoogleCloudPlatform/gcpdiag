<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
---
title: "gce/Auth Principal Has Os Login Permissions Check"
linkTitle: "Auth Principal Has Os Login Permissions Check"
weight: 3
type: docs
description: >
  Evaluates whether the user has the necessary IAM roles to use OS Login access a GCE instance.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step ensures the user possesses one of the required roles: OS Login User, OS Login Admin,
  or Project Owner, which are essential for accessing instances via the OS Login feature.
  A failure indicates the need to adjust IAM policies.

### Failure Reason

"{auth_user}" is missing at least one of the required OS Login roles:
{os_login_role}, {os_login_admin_role}, or {owner_role}.

### Failure Remediation

Assign "{auth_user}" one of the role required to have OS Login privileges.
For more information:
https://cloud.google.com/compute/docs/oslogin/set-up-oslogin#configure_users
https://cloud.google.com/iam/docs/manage-access-service-accounts#grant-single-role

### Success Reason

"{auth_user}" possesses at least one of the required OS Login roles:
{os_login_role}, {os_login_admin_role}, or {owner_role}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
