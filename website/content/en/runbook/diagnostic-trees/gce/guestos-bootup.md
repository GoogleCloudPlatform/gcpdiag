---
title: "gce/Guestos Bootup"
linkTitle: "gce/guestos-bootup"
weight: 3
type: docs
description: >
  Google Compute Engine VM Guest OS boot-up runbook.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook is designed to investigate the various boot-up stages of a Linux or Windows Guest
    OS running on Google Compute Engine. It is intended to help you identify and troubleshoot issues
    that may arise during the boot process. The runbook provides a structured approach to resolve
    issues.

    Key Investigation Areas:

    Boot Issues:
        - Check for Boot issues happening due to Kernel panics
        - Check for GRUB related issues.
        - Check if system failed to find boot disk.
        - Check if Filesystem corruption is causing issues with system boot.
        - Check if "/" Filesystem consumption is causing issues with system boot.

    Cloud-init checks:
        - Check if cloud-init has initialised or started.
        - Check if NIC has received the IP.

    Network related issues:
        - Check if metadata server became unreachable since last boot.
        - Check if there are any time sync related errors.

    Google Guest Agent checks:
        - Check if there are logs related to successful startup of Google Guest Agent.

### Executing this runbook

```shell
gcpdiag runbook gce/guestos-bootup \
  -p project_id=value \
  -p instance_name=value \
  -p instance_id=value \
  -p zone=value \
  -p serial_console_file=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID associated with the VM |
| `instance_name` | True | None | str | The name of the VM |
| `instance_id` | False | None | str | The instance-id of the VM |
| `zone` | True | None | str | The Google Cloud zone where the VM is located. |
| `serial_console_file` | False | None | str | Absolute path of files contailing the Serial console logs, in case if gcpdiag is not able to reach the VM Serial logs. i.e -p serial_console_file="filepath1,filepath2"  |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Guestos Bootup Start](/runbook/steps/gce/guestos-bootup-start)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Cloud Init Checks](/runbook/steps/gce/cloud-init-checks)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [End Step](/runbook/steps/gcpdiag/end-step)


<!--
This file is auto-generated. DO NOT EDIT.
-->
