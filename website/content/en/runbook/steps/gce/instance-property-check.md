---
title: "gce/Instance Property Check"
linkTitle: "Instance Property Check"
weight: 3
type: docs
description: >
  Checks that a Instance property meets a given condition.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step fetches a VM instance and checks if a specified property
  meets the condition defined by an expected value and an operator.
  It supports nested properties via getattr and various operators including
  'eq', 'ne', 'lt', 'le', 'gt', 'ge', 'contains', and 'matches'.

  Parameters:
  - property_path: The path of the property to check on the Instance object
    (e.g., 'status', 'boot_disk_licenses').
  - expected_value: The value to compare against. Supports 'ref:' prefix to
    resolve constants from gce/constants.py (e.g., 'ref:RHEL_PATTERN').
  - operator: The comparison operator to use. Supported: 'eq', 'ne',
    'lt', 'le', 'gt', 'ge', 'contains', 'matches'. Default is 'eq'.

  Operator Notes:
  - `contains`: Checks for exact membership in lists (e.g., 'item' in ['item'])
    or substring in strings.
  - `matches`: Treats `expected_value` as a regex and checks if the pattern is
    found in the string or in *any* element of a list. Useful for partial
    matches (e.g., pattern 'sles' matching license 'sles-12-sap').

### Failure Reason

Instance {instance_name} property '{property_path}' with value '{actual_value}' does not meet condition: {operator} '{expected_value}'.

### Failure Remediation

Ensure that property '{property_path}' for instance {instance_name} is configured to meet the condition: {operator} '{expected_value}'.

### Success Reason

Instance  property '{property_path}' with value '{actual_value}' meets condition: {operator} '{expected_value}'.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
