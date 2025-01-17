---
title: "vertex/Decision Check Workbench Instance System Logging"
linkTitle: "Decision Check Workbench Instance System Logging"
weight: 3
type: docs
description: >
  Decision point to investigate Serial Port Logs
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: GATEWAY

### Description

Decides whether its possible to check syslogs for the
  Workbench Instance

### Success Reason

OK! Workbench Instance {instance_name} Serial Port Logging is enabled and instance is initializing.
Checking Workbench Instance syslogs for issues

### Uncertain Reason

Workbench Instance {instance_name} Serial Port Logging is disabled by org constraint '{constraint}'

### Uncertain Remediation

Remove org constraint '{constraint}' to analyze Workbench Instance system serial port logs.


### Uncertain Reason [Alternative 2]

Workbench Instance {instance_name} not in PROVISIONING, STARTING or INITIALIZING state.
Current state: {state}

### Uncertain Remediation [Alternative 2]

Try to start the instance.


<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
