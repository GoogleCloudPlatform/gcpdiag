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

This step is crucial for confirming the VM's availability and operational readiness.
  It checks the VM's lifecycle state and reports success if the VM is running or fails the
  check if the VM is in any other state, providing detailed status information for
  troubleshooting.

### Failure Reason

The GCE VM {vm_name} is in an undesired state: {status}.

### Failure Remediation

This step failed because GCE Virtual Machine {vm_name} is expected to be in a RUNNING state:

To initiate the lifecycle transition from {status} to RUNNING state follow guide [1]

If you encounter any difficulties during the startup process, consult the troubleshooting
documentation to identify and resolve potential startup issues [2]
Resources:
[1] https://cloud.google.com/compute/docs/instances/stop-start-instance#restart-vm
[2] https://cloud.google.com/compute/docs/troubleshooting/vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting

### Success Reason

The GCE VM {vm_name} is in the expected state: {status}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
