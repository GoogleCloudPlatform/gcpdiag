---
title: "vertex/Check Workbench Instance Compute Engine S S H"
linkTitle: "Check Workbench Instance Compute Engine S S H"
weight: 3
type: docs
description: >
  Check if user is able to SSH to the Workbench Instance Compute Engine VM
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: COMPOSITE STEP

### Description

Compute Engine might be running so the user can ssh to
  inspect the VM

### Success Reason

OK! User can SHH and open a terminal in the Workbench Instance {instance_name}'s Compute Engine VM.

### Uncertain Reason

Workbench Instance {instance_name}'s Compute Engine VM is not running.
Status: {status}
You cannot ssh to use terminal access and check for certain issues in the VM.
For example, space in "/home/jupyter" directory should remain below 85%

### Uncertain Remediation

Try restarting your instance or start your instance's VM via Compute Engine



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
