---
title: "vertex/Check Workbench Instance Using Custom Container"
linkTitle: "Check Workbench Instance Using Custom Container"
weight: 3
type: docs
description: >
  Check if the Workbench Instance is using a custom container
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

Users have the option to use custom containers to create Workbench Instances
  If this is the case, this runbook doesn't apply

### Success Reason

OK! Workbench Instance {instance_name} is not using a custom container.

### Uncertain Reason

WARNING: This runbook may not be applicable for Workbench Instances created with a custom container.

### Uncertain Remediation

Follow the documentation to create a Workbench Instance with a custom container [1]
[1] https://cloud.google.com/vertex-ai/docs/workbench/instances/create-custom-container



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
