---
title: "gce/High Vm Memory Utilization"
linkTitle: "High Vm Memory Utilization"
weight: 3
type: docs
description: >
  Diagnoses high memory utilization issues in a Compute Engine VM.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

This step evaluates memory usage through available monitoring data or, as a fallback, scans serial
  logs for Out of Memory (OOM) indicators. It distinguishes between VMs which has exported metrics
  and those without, and employs a different strategy for 'e2' machine types to accurately assess
  memory utilization.

### Failure Reason

Memory utilization on this VM has reached levels that may compromise its VM application performance.

### Failure Remediation

Elevated memory usage can result in slow or unresponsive or termimated applications.
Consider enhancing the VM's memory capacity by changing to a machine type with more memory.
Guidance on stopping and changing the machine type can be found here:
- Changing machine type:
https://cloud.google.com/compute/docs/instances/changing-machine-type-of-stopped-instance#gcloud

Additionally, use the Compute Engine observability metrics for an in-depth analysis to pinpoint high-usage processes:
https://cloud.google.com/compute/docs/instances/observe-monitor-vms#memory_utilization

Or connect via the Serial Console if SSH is not available to mitigate the issue:
https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-using-serial-console

### Success Reason

Memory utilization on this VM is within optimal range.

### Skipped Reason

There are no logs to examine!



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
