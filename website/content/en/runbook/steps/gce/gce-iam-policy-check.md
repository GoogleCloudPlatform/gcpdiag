---
title: "gce/Gce Iam Policy Check"
linkTitle: "Gce Iam Policy Check"
weight: 3
type: docs
description: >
  Checks IAM policies by calling IamPolicyCheck with support for gce/constants.py.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step is a wrapper around iam.generalized_steps.IamPolicyCheck that adds
  support for resolving 'roles' or 'permissions' parameters from gce/constants.py
  if they are prefixed with 'ref:'. It also supports ';;' delimited strings for
  roles or permissions lists.

  Parameters retrieved via `op.get()`:
    project_id(str): Project ID to check policy against.
    principal(str): The principal to check (e.g., user:x@y.com,
      serviceAccount:a@b.com).
    roles(Optional[str]): ';;' separated list of roles or 'ref:CONSTANT' to check.
    permissions(Optional[str]): ';;' separated list of permissions or
      'ref:CONSTANT' to check.
    require_all(bool): If True, all roles/permissions must be present.
      If False (default), at least one must be present.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
