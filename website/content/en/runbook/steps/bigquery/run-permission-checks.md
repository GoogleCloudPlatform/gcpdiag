---
title: "bigquery/Run Permission Checks"
linkTitle: "Run Permission Checks"
weight: 3
type: docs
description: >
  A comprehensive step to check all mandatory and optional permissions.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: GATEWAY

### Description

This step is intended to check mandatory and optional permissions for the
  given BigQuery runbook type. It will terminate runbook execution if mandatory
  permissions are missing, or add 'SKIP' notifications for missing optional
  permissions. The step execution will skip altogether if the user is missing
  the resourcemanager.projects.get permission. Finally, it populates the global
  PERMISSION_RESULTS dictionary used throughout the runbook.

### Failure Reason

Execution halted. The principal {principal} is missing the following mandatory IAM permission(s) required to run this runbook: {permissions}.

### Failure Remediation

Grant the principal {principal} the missing permission(s) on the project to proceed.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
