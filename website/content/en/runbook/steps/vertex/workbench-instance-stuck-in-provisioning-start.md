---
title: "vertex/Workbench Instance Stuck In Provisioning Start"
linkTitle: "Workbench Instance Stuck In Provisioning Start"
weight: 3
type: docs
description: >
  Checking if the Workbench Instance is in PROVISIONING state and gathering its details...
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: START

### Description

If the instance is stopped, user must try to start it to start the checks

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
