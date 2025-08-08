---
title: "gce/Vm Creation"
linkTitle: "gce/vm-creation"
weight: 3
type: docs
description: >
  Runbook for diagnosing VM creation issues.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook helps identify and resolve issues related to VM creation in Google Cloud.

    - Checks for quota-related issues.
    - Checks for permission-related issues.
    - Checks for conflicts such as resource already existing.

### Executing this runbook

```shell
gcpdiag runbook gce/vm-creation \
  -p project_id=value \
  -p instance_name=value \
  -p zone=value \
  -p principal=value \
  -p start_time=value \
  -p end_time=value \
  -p check_zone_separation_policy=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID which will host the VM to be created. |
| `instance_name` | True | None | str | The name of the VM to be created. |
| `zone` | True | None | str | The Google Cloud zone of the VM to be created. |
| `principal` | False | None | str | The authenticated principal that initiated the VM creation. |
| `start_time` | False | None | datetime | The start window to investigate vm termination. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |
| `check_zone_separation_policy` | False | False | bool | Check if the zone separation policy is enforced. |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Start Step](/runbook/steps/gcpdiag/start-step)

  - [Investigate Vm Creation Log Failure](/runbook/steps/gce/investigate-vm-creation-log-failure)

  - [Org Policy Check](/runbook/steps/crm/org-policy-check)

  - [End Step](/runbook/steps/gcpdiag/end-step)


<!--
This file is auto-generated. DO NOT EDIT.
-->
