---
title: "gce/Vm Has Ops Agent"
linkTitle: "Vm Has Ops Agent"
weight: 3
type: docs
description: >
  Verifies that a GCE Instance has at ops agent installed and
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

You can check for sub agents for logging and metrics

  Attributes
   - Set `check_logging` to check for logging sub agent. Defaults is True
   - Set `check_metrics` to check for metrics sub agent. Default is True

### Failure Reason

GCE Instance "{full_resource_path}" does not have {subagent} agent installed and is not exporting data.

### Failure Remediation

Install the {subagent} agent on GCE Instance "{full_resource_path}".
Consult the following documentation for troubleshooting assistance:
<https://cloud.google.com/stackdriver/docs/solutions/agents/ops-agent/troubleshoot-run-ingest>

### Success Reason

GCE Instance "{full_resource_path}" has {subagent} agent installed and is exporting data.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
