---
title: "gce/Serial Log Analyzer Start"
linkTitle: "Serial Log Analyzer Start"
weight: 3
type: docs
description: >
  Fetching VM details.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: START

### Description

None

### Failure Reason

The GCE Instance {full_resource_path} is in {status} state.

### Failure Remediation

Restart VM {full_resource_path} and ensure VM lifecycle transitions from {status} to RUNNING.

Consult the following documentation:

- Restarting a compute instance:
  <https://cloud.google.com/compute/docs/instances/stop-start-instance#restart-vm>
- Troubleshooting VM startup issues:
  <https://cloud.google.com/compute/docs/troubleshooting/vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting>

### Success Reason

The GCE Instance {full_resource_path} is in {status} state.

### Skipped Reason

Could not validate VM lifecycle for GCE Instance {full_resource_path}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
