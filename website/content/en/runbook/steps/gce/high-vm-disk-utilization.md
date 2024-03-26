<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
---
title: "gce/High Vm Disk Utilization"
linkTitle: "High Vm Disk Utilization"
weight: 3
type: docs
description: >
  Assesses disk utilization on a VM, aiming to identify high usage that could impact performance.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step leverages monitoring data if the Ops Agent is exporting disk usage metrics.
  Alternatively, it scans the VM's serial port output for common disk space error messages.
  This approach ensures comprehensive coverage across different scenarios,
  including VMs without metrics data.

### Failure Reason

Disk utilization on this VM's boot disk is critically high,
potentially affecting application performance.

### Failure Remediation

To mitigate high disk usage, consider expanding the VM's boot disk capacity.
This action can help avoid performance issues and ensure smoother SSH connections.
Follow the guide to increase disk size:
https://cloud.google.com/compute/docs/disks/resize-persistent-disk#increase_the_size_of_a_disk

### Success Reason

The VM's disk space usage is within optimal levels.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
