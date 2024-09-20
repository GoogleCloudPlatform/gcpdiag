---
title: "gce/Serial Log Analyzer"
linkTitle: "gce/serial-log-analyzer"
weight: 3
type: docs
description: >
  Google Compute Engine VM Serial log analyzer
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook is designed to assist you in investigating the serial console logs of a vm.

    Key Investigation Areas:

    Boot Issues:
        - Check for Boot issues happening due to Kernel Panics
        - Check for GRUB related issues.
        - Check if system failed to find boot disk.
        - Check if Filesystem corruption is causing issues with system boot.
        - Check if "/" Filesystem consumption is causing issues with system boot.

    Memory crunch issues:
        - Check if OOM kills happened on the VM or any other memory related issues.

    Cloud-init checks:
        - Check if cloud-init has initialised or started.
        - Check if NIC has received the IP.

    Network related issues:
        - Check if metadata server became unreachable since last boot.
        - Check if there are any time sync related errors.

    SSHD checks:
        - Check if we have logs related to successful startup of SSHD service.

    SSHD Auth Failures checks:
        - Check for SSH issues due to bad permissions of files or directories

    Google Guest Agent checks:
        - Check if we have logs related to successful startup of Google Guest Agent.

    SSH guard check:
        - Check if SSHGuard is active and may be blocking IP addresses

### Executing this runbook

```shell
gcpdiag runbook gce/serial-log-analyzer \
  -p project_id=value \
  -p name=value \
  -p id=value \
  -p zone=value \
  -p serial_console_file=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID associated with the VM for which you want to                 analyse the Serial logs. |
| `name` | True | None | str | The name of the VM, for which you want to analyse the Serial logs. Or provide the id i.e -p name=<str> |
| `id` | False | None | str | The instance-id of the VM, for which you want to analyse the Serial logs. Or provide the id i.e -p id=<int> |
| `zone` | True | None | str | The Google Cloud zone where the VM is located. |
| `serial_console_file` | False | None | str | Absolute path of files contailing the Serial console logs, in case if gcpdiag is not able to reach the VM Serial logs. i.e -p serial_console_file="filepath1,filepath2"  |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Fetch Vm Details](/runbook/steps/gce/fetch-vm-details)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Cloud Init Checks](/runbook/steps/gce/cloud-init-checks)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Analysing Serial Logs End](/runbook/steps/gce/analysing-serial-logs-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
