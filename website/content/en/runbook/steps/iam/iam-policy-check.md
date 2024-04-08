---
title: "iam/Iam Policy Check"
linkTitle: "Iam Policy Check"
weight: 3
type: docs
description: >
  Checks if a principal has specified permissions or is a member of specified roles.
---

**Product**: [Identity and Access Management (IAM)](https://cloud.google.com/iam)\
**Step Type**: AUTOMATED STEP

### Description

This step supports checking for either all specified permissions/roles are present or
  at least one for the principal (user or service account). It reports the present and missing
  permissions/roles accordingly. Also, identifying which permissions or roles
  are present and which are missing.

  Attributes:
    principal (str): The identifier for the principal whose permissions are being checked.
    permissions (Optional[Set[str]]): A set of IAM permissions to check. Specify this or `roles`.
    roles (Optional[Set[str]]): A set of IAM roles to check. Specify this or `permissions`.
    require_all (bool): If True, requires all specified permissions or roles to be present. If
                        False, requires at least one of the specified permissions or roles to be
                        present.
    template (str): The template used for generating reports for the step.

### Failure Reason

{principal} doesn't have at least one of the expected {permissions_or_roles}:
{missing_permissions_or_roles}.

### Failure Remediation

Follow Guide [1] to grant a role which has the correct permissions.
[2] has a list of all Google predefined roles available to you.

Note: You may want to doublecheck with your project admins of the best way to grant the role
or custom roles which can be used.

[1] https://cloud.google.com/iam/docs/grant-role-console
[2] https://cloud.google.com/iam/docs/understanding-roles

### Success Reason

{principal} has expected {permissions_or_roles}.
{present_permissions_or_roles}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
