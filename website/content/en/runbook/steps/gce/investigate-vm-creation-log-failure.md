---
title: "gce/Investigate Vm Creation Log Failure"
linkTitle: "Investigate Vm Creation Log Failure"
weight: 3
type: docs
description: >
  Investigate VM creation failure logs.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: GATEWAY

### Description

This step queries logs to identify the root cause of VM creation failures,
    such as quota issues, permission errors, or resource conflicts.

### Failure Reason

{error_message}

### Failure Remediation

The VM creation process failed because the VM `{instance_name}` already exists in zone `{zone}` within project `{project_id}`. Delete the existing VM or choose a different name for the new VM.


### Failure Reason [Alternative 2]

{error_message}

### Failure Remediation [Alternative 2]

Grant the user or service account attempting the VM creation the required permissions to create a VM instance.
Consult the following guide for details on required permissions:
<https://cloud.google.com/compute/docs/instances/create-start-instance#expandable-1>


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
