---
title: "vertex/Check Workbench Instance Jupyter Space"
linkTitle: "Check Workbench Instance Jupyter Space"
weight: 3
type: docs
description: >
  Check if Jupyter space in "home/jupyter" is below 85%
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

If Jupyter has ran out of space, the Workbench Instance
  might not be able to start

### Failure Reason

Workbench Instance {instance_name}'s space in "/home/jupyter" should remain below 85%
This will allow the instance to start correctly.

### Failure Remediation

Delete large files in "/home/jupyter" and restart the instance.
You may also run the following command to list large cache files and then manually delete them.
- "du -h /home/jupyter/.cache | sort -h"

### Success Reason

OK! Workbench Instance {instance_name}'s "/home/jupyter" space usage is below 85%



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
