---
title: "iam/Iam Policy Check"
linkTitle: "Iam Policy Check"
weight: 3
type: docs
description: >
  Verify if specificd principal has permissions or roles permission/role in project.
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

{principal} does not have at least one of the expected {permissions_or_roles}:
{missing_permissions_or_roles}.

### Failure Remediation

Grant a role containing the missing permissions by following the instructions in [1].
Refer to [2] for a list of Google Cloud predefined roles.

Note: Consider consulting with project administrators regarding the most appropriate standard or custom role to grant.

[1] <https://cloud.google.com/iam/docs/grant-role-console>
[2] <https://cloud.google.com/iam/docs/understanding-roles>

### Success Reason

{principal} has expected {permissions_or_roles}.
{present_permissions_or_roles}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
