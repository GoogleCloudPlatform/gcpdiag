---
title: "gce/Mig Autoscaling Policy Check"
linkTitle: "Mig Autoscaling Policy Check"
weight: 3
type: docs
description: >
  Checks MIG autoscaling policy attributes.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step performs checks on attributes within a Managed Instance Group (MIG)'s
  autoscaling policy. It requires both 'property_path' and 'expected_value' to be
  specified.

  The MIG can be identified either by providing 'instance_name' and 'zone' (the
  step will find the MIG associated with the instance) or by providing 'mig_name'
  and 'location' (zone or region).

  Parameters:
  - property_path: The nested path of the property to check within the MIG or
    autoscaler resource (e.g., 'autoscalingPolicy.mode'). If the path starts
    with 'autoscalingPolicy', the autoscaler resource is queried.
  - expected_value: The value to compare against. Supports 'ref:' prefix to
    resolve constants from gce/constants.py (e.g., 'ref:AUTOSCALING_MODE_ON').
  - operator: The comparison operator to use. Supported: 'eq' (default), 'ne',
    'lt', 'le', 'gt', 'ge'.

### Failure Reason

MIG {mig_name} property '{property_path}' with value '{actual_value}' does not meet condition: {operator} '{expected_value}'.

### Failure Remediation

Review the autoscaling policy for MIG {mig_name} and ensure it meets the required configuration.
See: <https://cloud.google.com/compute/docs/reference/rest/v1/instanceGroupManagers>

### Success Reason

MIG {mig_name} property '{property_path}' with value '{actual_value}' meets condition: {operator} '{expected_value}'.

### Skipped Reason

MIG could not be determined or found.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
