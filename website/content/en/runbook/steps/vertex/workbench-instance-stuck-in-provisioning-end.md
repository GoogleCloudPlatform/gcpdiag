---
title: "vertex/Workbench Instance Stuck In Provisioning End"
linkTitle: "Workbench Instance Stuck In Provisioning End"
weight: 3
type: docs
description: >
  Checking if the Workbench Instance is now in ACTIVE state...
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: END

### Description

If Workbench Instance is still stuck in PROVISIONING state, then
  Diagnostic Logs should be captured and analyzed by the user or support

### Failure Reason

Workbench Instance {instance_name} not in PROVISIONING, STARTING or INITIALIZING state.

### Failure Remediation

Try to start the instance.

### Success Reason

OK! Workbench Instance {instance_name} is already in ACTIVE state.
WARNING: This runbook is intended for instances that are stuck in PROVISIONING state.

### Uncertain Reason

Workbench Instance {instance_name} not in PROVISIONING, STARTING or INITIALIZING state.

### Uncertain Remediation

Try to start the instance.


### Success Reason [Alternative 2]

OK! Workbench Instance {instance_name} is already in ACTIVE state.
The issue is solved!!!


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
