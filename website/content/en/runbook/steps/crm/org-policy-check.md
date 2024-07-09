---
title: "crm/Org Policy Check"
linkTitle: "Org Policy Check"
weight: 3
type: docs
description: >
  Checks if an organization policy is effective in a project
---

**Product**: \
**Step Type**: AUTOMATED STEP

### Description

Supports only boolean constraints and not list constraints.

### Failure Reason

The {constraint} policy is {actual_state} however should be {expected_state}.

### Failure Remediation

Follow Guide [1] to correct the constraint. Search for the constraint in [2] to better understand
how it works.

Note: You may want to doublecheck with your organization admins of the best approach here.

[1] https://cloud.google.com/resource-manager/docs/organization-policy/using-constraints
[2] https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints

### Success Reason

The {constraint} is {actual_state}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
