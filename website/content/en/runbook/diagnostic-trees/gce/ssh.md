<!--
This file is auto-generated. DO NOT EDIT.
-->
---
title: "gce/Ssh"
linkTitle: "gce/ssh"
weight: 3
type: docs
description: >
  Provides a comprehensive analysis of common issues which affects SSH connectivity to VMs.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

This runbook focuses on a range of potential problems for both Windows and Linux VMs on
  Google Cloud Platform. By conducting a series of checks, the runbook aims to pinpoint the
  root cause of SSH access difficulties.

  The following areas are examined:

  - VM Instance Status: Evaluates the VM's current state, performance - ensuring that it is running
    and not impaired by high CPU usage, insufficient memory, or disk space issues that might disrupt
    normal SSH operations.

  - User Permissions: Checks for the necessary Google Cloud IAM permissions that are required to
    leverage OS Login features and to use metadata-based SSH keys for authentication.

  - VM Configuration: Analyzes the VM's metadata settings to confirm the inclusion of SSH keys,
    flags and other essential configuration details that facilitate SSH access.

  - GCE Network Connectivity Tests: Reviews applicable firewall rules to verify that there are no
    network barriers preventing SSH access to the VM.

  - Internal Guest OS Checks: Analysis available Guest OS metrics or logs to detect any
    misconfigurations or service disruptions that could be obstructing SSH functionality.

### Executing this runbook

```shell
gcpdiag runbook gce/ssh \
  -p project_id = value \
  -p name = value \
  -p zone = value \
  -p principal = value \
  -p local_user = value \
  -p tunnel_through_iap = value \
  -p check_os_login = value \
  -p src_ip = value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the VM |
| `name` | True | None | str | The name or instance ID of the target VM |
| `zone` | True | None | str | The zone of the target VM |
| `principal` | True | None | str | The user or service account principal initiating the SSH connection this user should be authenticated in gcloud/cloud console when sshing into to the GCE. For service account impersonation, it should be the service account's email |
| `local_user` | False | None | str | Poxis User on the VM |
| `tunnel_through_iap` | False | True | bool | ('A boolean parameter (true or false) indicating whether ', 'Identity-Aware Proxy should be used for establishing the SSH connection.') |
| `check_os_login` | False | True | bool | A boolean value (true or false) indicating whether OS Login should be used for SSH authentication |
| `src_ip` | False | 35.235.240.0/20 | IPv4Address | Source IP address. Workstation connecting from workstation,Ip of the bastion/jumphost if currently on logged on a basition/jumphost  |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Ssh Start](/runbook/steps/gce/ssh-start)

  - [Vm Lifecycle State](/runbook/steps/gce/vm-lifecycle-state)

  - [Vm Performance Checks](/runbook/steps/gce/vm-performance-checks)

  - [High Vm Memory Utilization](/runbook/steps/gce/high-vm-memory-utilization)

  - [High Vm Disk Utilization](/runbook/steps/gce/high-vm-disk-utilization)

  - [High Vm Cpu Utilization](/runbook/steps/gce/high-vm-cpu-utilization)

  - [Vm Guest Os Type](/runbook/steps/gce/vm-guest-os-type)

  - [Linux Guest Os Checks](/runbook/steps/gce/linux-guest-os-checks)

  - [Windows Guest Os Checks](/runbook/steps/gce/windows-guest-os-checks)

  - [Gcp Ssh Permissions](/runbook/steps/gce/gcp-ssh-permissions)

  - [Auth Principal Cloud Console Permission Check](/runbook/steps/gce/auth-principal-cloud-console-permission-check)

  - [Auth Principal Has Permission To Fetch Vm Check](/runbook/steps/gce/auth-principal-has-permission-to-fetch-vm-check)

  - [Os Login Status Check](/runbook/steps/gce/os-login-status-check)

  - [Auth Principal Has Iap Tunnel User Permissions Check](/runbook/steps/gce/auth-principal-has-iap-tunnel-user-permissions-check)

  - [Gce Firewall Allows Ssh](/runbook/steps/gce/gce-firewall-allows-ssh)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Ssh End](/runbook/steps/gce/ssh-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
