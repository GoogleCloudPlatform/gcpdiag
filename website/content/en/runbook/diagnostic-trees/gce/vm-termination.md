---
title: "gce/Vm Termination"
linkTitle: "gce/vm-termination"
weight: 3
type: docs
description: >
  GCE Instance unexpected shutdowns and reboots diagnostics
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook assists in investigating and understanding the reasons behind unexpected
  terminations or reboots of GCE Virtual Machines (VMs).

  Areas investigated:

  - System event-triggered shutdowns and reboots: Identifies terminations initiated by Google Cloud
    systems due to maintenance events, hardware failures, or resource constraints.

  - Admin activities-triggered shutdown/reboot: Investigates terminations caused by direct actions,
    such as API calls made by users or service accounts, including manual shutdowns, restarts, or
    automated processes impacting VM states.

### Executing this runbook

```shell
gcpdiag runbook gce/vm-termination \
  -p project_id=value \
  -p instance_name=value \
  -p instance_id=value \
  -p zone=value \
  -p start_time=value \
  -p end_time=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID hosting the terminated VM. |
| `instance_name` | True | None | str | The name of the terminated VM. Or provide the id i.e -p id=<int> |
| `instance_id` | False | None | int | The instance ID of the terminated VM. Or provide name instead i.e -p name=<str> |
| `zone` | True | None | str | The Google Cloud zone where the terminated VM is located. |
| `start_time` | False | None | datetime | The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Vm Termination Start](/runbook/steps/gce/vm-termination-start)

  - [Termination Operation Type](/runbook/steps/gce/termination-operation-type)

  - [Managed Instance Group Recreation](/runbook/steps/gce/managed-instance-group-recreation)

  - [Preemptible Instance](/runbook/steps/gce/preemptible-instance)

  - [Host Error](/runbook/steps/gce/host-error)

  - [Guest Os Issued Shutdown](/runbook/steps/gce/guest-os-issued-shutdown)

  - [Terminate On Host Maintenance](/runbook/steps/gce/terminate-on-host-maintenance)

  - [Stop Operation Gateway](/runbook/steps/gce/stop-operation-gateway)

  - [Vm Termination End](/runbook/steps/gce/vm-termination-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
