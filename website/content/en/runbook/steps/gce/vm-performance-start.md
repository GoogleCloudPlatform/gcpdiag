---
title: "gce/Vm Performance Start"
linkTitle: "Vm Performance Start"
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

The GCE VM {vm_full_path} is in an undesired state: {status}.

### Failure Remediation

This step failed because GCE Virtual Machine {vm_full_path} is expected to be in a RUNNING state:

To initiate the lifecycle transition from {status} to RUNNING state follow guide [1]

If you encounter any difficulties during the startup process, consult the troubleshooting
documentation to identify and resolve potential startup issues [2]
Resources:
[1] https://cloud.google.com/compute/docs/instances/stop-start-instance#restart-vm
[2] https://cloud.google.com/compute/docs/troubleshooting/vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting

### Success Reason

The GCE VM {vm_full_path} is in {status} state.

### Skipped Reason

Could not validate VM lifecycle.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
