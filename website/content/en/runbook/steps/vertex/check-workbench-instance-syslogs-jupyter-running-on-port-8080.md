---
title: "vertex/Check Workbench Instance Syslogs Jupyter Running On Port 8080"
linkTitle: "Check Workbench Instance Syslogs Jupyter Running On Port 8080"
weight: 3
type: docs
description: >
  Check Jupyter is running on port 127.0.0.1:8080
---

**Product**: [Vertex AI](https://cloud.google.com/vertex-ai)\
**Step Type**: AUTOMATED STEP

### Description

Jupyter should always run on port 127.0.0.1:8080
  for the Workbench Instance to work correctly

### Failure Reason

Workbench Instance {instance_name} syslogs indicate Jupyter is NOT running on port 127.0.0.1:8080

### Failure Remediation

If the instance is stopped, start it and rerun this check.
You may also need to extend the logging query start and end times.
Only port 8080 is supported. Installed extensions, packages or custom scripts may cause the port to change.

1. Try following documentation [1] [2] [3]
2. If it doesn't work, recover data by diagnosing the instance with the --enable-copy-home-files [4]
3. Create a new Instance and migrate your data [5]

[1] <https://cloud.google.com/vertex-ai/docs/general/troubleshooting-workbench?component=any#verify-jupyter-service>
[2] <https://cloud.google.com/vertex-ai/docs/general/troubleshooting-workbench?component=any#verify-jupyter-internal-api>
[3] <https://cloud.google.com/vertex-ai/docs/general/troubleshooting-workbench?component=any#restart-jupyter-service>
[4] <https://cloud.google.com/sdk/gcloud/reference/workbench/instances/diagnose>
[5] <https://cloud.google.com/vertex-ai/docs/workbench/instances/migrate>

### Success Reason

OK! Workbench Instance {instance_name} syslogs indicate Jupyter is running on port 127.0.0.1:8080



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
