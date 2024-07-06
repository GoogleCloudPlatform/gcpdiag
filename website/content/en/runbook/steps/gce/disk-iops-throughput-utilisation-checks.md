---
title: "gce/Disk Iops Throughput Utilisation Checks"
linkTitle: "Disk Iops Throughput Utilisation Checks"
weight: 3
type: docs
description: >
  Checking if the Disk IOPS/throughput usage is within optimal levels
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Disk IOPS/Throughput usage is NOT within optimal limits

### Failure Remediation

There can be multiple reasons which can cause Disk IOPS/Throughput usage to increase:

- Application and GuestOS Operations - Unmanaged and untested application workloads can cause the high influx of IOs
  to the disk and cause IO operations to be queued, causing throttling at disk levels.

- CPU Starvation - Small instances(with lesser CPUs) may not have enough CPU to serve all I/Os inflight.
  https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-performance#cpu_and_memory_performance

- Network Throttling - High sent/received network traffic can cause network throttling, that can also impacts disk operations.
  https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-performance#network_performance

- Insufficient Machine Resources - If your machine's IOPS and throughput limts are not enought to serve your workloads,
  this can also cause CPU or Disk IOPS/throughput Starvation.
  https://cloud.google.com/compute/docs/troubleshooting/troubleshooting-performance#storage_performance

To fix this issue:
 - Please optmize your application workloads.
 - If needed, please add more resources(CPU, Memory) to the VM.
 - Please optmize your Disk performance -
    https://cloud.google.com/compute/docs/disks/optimizing-pd-performance
 - If needed, please change your disk type to get better Disk IOPS/throughput limits -
    https://cloud.google.com/compute/docs/disks/modify-persistent-disk#disk_type




<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
