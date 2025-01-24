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

The GCE Instance {full_resource_path} is not in the {status}.

### Failure Remediation

Restart VM {full_resource_path} and ensure VM lifecycle transitions from {status} to RUNNING.

You can [restart a compute instance](https://cloud.google.com/compute/docs/instances/stop-start-instance#restart-vm)
with this guide.

If you encounter any difficulties starting the VM, consult the [VM Startup troubleshooting
documentation](https://cloud.google.com/compute/docs/troubleshooting/vm-startup#identify_the_reason_why_the_boot_disk_isnt_booting)
to identify and resolve potential startup issues.

### Success Reason

The GCE Instance {full_resource_path} is in {status} state.

### Skipped Reason

Could not validate VM lifecycle.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
