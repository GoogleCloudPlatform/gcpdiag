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

GCE VM {vm_name} is in {status} state.

### Failure Remediation

To initiate the lifecycle transition of Virtual Machine (VM) {vm_name} to the RUNNING state:
Start the VM:
https://cloud.google.com/compute/docs/instances/stop-start-instance
If you encounter any difficulties during the startup process, consult the troubleshooting
documentation to identify and resolve potential startup issues:
https://cloud.google.com/compute/docs/troubleshooting/vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting

### Success Reason

GCE VM {vm_name} is in a {status} state.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
