---
title: "gce/Vm Performance"
linkTitle: "gce/vm-performance"
weight: 3
type: docs
description: >
  Google Compute Engine VM performance checks
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook is designed to assist you in investigating and understanding the underlying reasons
  behind the performance issues of your Google Compute Engine VMs within Google Cloud Platform.

  Key Investigation Areas:

    - High CPU utilisation
    - CPU Over-commitment for E2 or Sole-Tenant VMs
    - High Memory utilisation
    - Disk space high utilisation
    - High Disk IOPS utilisation
    - High Disk Throughput utilisation
    - Disk Health check
    - Disk IO latency check
    - Disk Slowness check
    - Check for Live Migrations
    - Usual Error checks in Serial console logs

### Executing this runbook

```shell
gcpdiag runbook gce/vm-performance \
  -p project_id=value \
  -p name=value \
  -p zone=value \
  -p start_time_utc=value \
  -p end_time_utc=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID associated with the VM having performance issues. |
| `name` | True | None | str | The name of the VM having performance issues. Or provide the id i.e -p name=<int> |
| `zone` | True | None | str | The Google Cloud zone where the VM having performance issues, is located. |
| `start_time_utc` | False | None | datetime | The start window(in UTC) to investigate vm performance issues.Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time_utc` | False | None | datetime | The end window(in UTC) for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Vm Performance Start](/runbook/steps/gce/vm-performance-start)

  - [Vm Lifecycle State](/runbook/steps/gce/vm-lifecycle-state)

  - [High Vm Cpu Utilization](/runbook/steps/gce/high-vm-cpu-utilization)

  - [Cpu Overcommitment Check](/runbook/steps/gce/cpu-overcommitment-check)

  - [High Vm Memory Utilization](/runbook/steps/gce/high-vm-memory-utilization)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Disk Health Check](/runbook/steps/gce/disk-health-check)

  - [High Vm Disk Utilization](/runbook/steps/gce/high-vm-disk-utilization)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Disk Avg Io Latency Check](/runbook/steps/gce/disk-avg-io-latency-check)

  - [Check Live Migrations](/runbook/steps/gce/check-live-migrations)

  - [Disk Iops Throughput Utilisation Checks](/runbook/steps/gce/disk-iops-throughput-utilisation-checks)

  - [Disk Iops Throughput Utilisation Checks](/runbook/steps/gce/disk-iops-throughput-utilisation-checks)

  - [Vm Performance End](/runbook/steps/gce/vm-performance-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
