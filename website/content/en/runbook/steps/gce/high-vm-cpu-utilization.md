---
title: "gce/High Vm Cpu Utilization"
linkTitle: "High Vm Cpu Utilization"
weight: 3
type: docs
description: >
  Evaluates the CPU of a VM for high utilization that might indicate performance issues.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step determines whether the CPU utilization of the VM exceeds a predefined threshold,
  indicating potential performance degradation. It utilizes metrics from the Ops Agent if installed,
  or hypervisor-visible metrics as a fallback, to accurately assess CPU performance and identify any
  issues requiring attention.

### Failure Reason

CPU utilization on this VM has surpassed recommended operational levels,
which may affect its performance and SSH connectivity.

### Failure Remediation

Excessive CPU usage can lead to performance bottlenecks. Resizing the VM to a machine type with higher CPU capabilities may resolve the issue.

Consult the following documentation for guidance:

- Stopping a VM: <https://cloud.google.com/compute/docs/instances/stop-start-instance>
- Resizing a VM: <https://cloud.google.com/compute/docs/instances/changing-machine-type-of-stopped-instance#gcloud>

Additionally, analyze Compute Engine observability metrics to pinpoint high-usage processes:

- Accessing VM observability metrics:
  <https://cloud.google.com/compute/docs/instances/observe-monitor-vms#access_vm_observability_metrics>
- Analyzing process utilization:
  <https://cloud.google.com/compute/docs/instances/observe-monitor-vms#process_utilization>

If SSH is unavailable, connect via the serial console to stop offending processes:
<https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-using-serial-console>

### Success Reason

The Compute Engine VM {full_resource_path},
has CPU utilization within the optimal range.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
