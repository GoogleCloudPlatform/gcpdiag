---
title: "vertex/Check Workbench Instance Custom Scripts"
linkTitle: "Check Workbench Instance Custom Scripts"
weight: 3
type: docs
description: >
  Check if the Workbench Instance is using custom scripts
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

Users have the option to add scripts to a Workbench Instance
  via the metadata fields. However, scripts may change the
  default behaviour or install libraries that break dependencies

### Success Reason

OK! Workbench Instance {instance_name} is not using custom post-startup or startup scripts.

### Uncertain Reason

Workbench Instance {instance_name} has custom post-startup or startup scripts:
- post-startup-script: {post_startup_script}
- startup-script: {startup_script}
- startup-script-url: {startup_script_url}

### Uncertain Remediation

Scripts must ensure:
- Jupyter runs on port 127.0.0.1:8080
- If packages are installed they should not add breaking changes to the Jupyter configuration



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
