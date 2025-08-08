---
title: "bigquery/Check Permissions"
linkTitle: "Check Permissions"
weight: 3
type: docs
description: >
  Checks for necessary IAM permissions to execute the runbook's diagnostic steps.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Principal `{principal}` is missing the following required permissions for the {runbook_id}: {missing_permissions_or_roles}.

### Failure Remediation

Grant the principal `{principal}` the necessary permissions, typically by assigning predefined IAM roles like '{required_roles}' at the project level.

### Success Reason

Principal `{principal}` has all required permissions for the {runbook_id}: {present_permissions_or_roles}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
