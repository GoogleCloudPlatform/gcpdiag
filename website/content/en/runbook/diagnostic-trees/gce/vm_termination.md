<!--
This file is auto-generated. DO NOT EDIT.
-->
---
title: "gce/Vm Termination"
linkTitle: "gce/vm_termination"
weight: 3
type: docs
description: >
  GCE VM shutdowns and reboots Root Cause Analysis (RCA)
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook is designed to assist you in investigating and understanding the underlying reasons
  behind the unexpected termination or reboot of your GCE Virtual Machines (VMs) within Google
  Cloud Platform.

  Key Investigation Areas:

  System Event-Triggered Shutdowns/Reboots: Identifies terminations initiated by internal Google
  Cloud systems due to system maintenance events, normal hardware failures,
  resource constraints.

  System Admin Activities-Triggered Shutdowns/Reboots: Investigates terminations caused by
  direct actions, such as API calls made by users or service accounts. These actions
  may include manual shutdowns, restarts, or automated processes impacting VM states.

  RCA Text Generation: Provides a detailed Root Cause Analysis text, outlining the identified
  cause of termination, the involved systems or activities, and recommendations
  to prevent future occurrences where applicaable.

### Executing this runbook

```shell
gcpdiag runbook gce/vm_termination \
  -p project_id = value \
  -p name = value \
  -p id = value \
  -p zone = value \
  -p start_time_utc = value \
  -p end_time_utc = value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID associated with the terminated VM.For investigations covering multiple VMs, provide only the Project ID. |
| `name` | False | None | str | The name of the terminated VM. Or provide the id i.e -p id=<int> |
| `id` | False | None | int | The instance ID of the terminated VM. Or provide name instead i.e -p name=<str> |
| `zone` | False | None | str | The Google Cloud zone where the terminated VM is located. |
| `start_time_utc` | False | None | datetime | The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time_utc` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Vm Termination Start](/runbook/steps/gce/vm-termination-start)

  - [Number Of Terminations](/runbook/steps/gce/number-of-terminations)

  - [Single Termination Check](/runbook/steps/gce/single-termination-check)

  - [Multiple Termination Check](/runbook/steps/gce/multiple-termination-check)

  - [Vm Termination End](/runbook/steps/gce/vm-termination-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
