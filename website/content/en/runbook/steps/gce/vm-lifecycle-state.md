---
title: "gce/Vm Lifecycle State"
linkTitle: "Vm Lifecycle State"
weight: 3
type: docs
description: >
  Validates that a specified VM is in the 'RUNNING' state.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step is crucial for confirming the VM's availability and operational
  readiness. It checks the VM's lifecycle state and reports success if the VM
  is running or fails the check if the VM is in any other state, providing
  detailed status information for troubleshooting.

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
