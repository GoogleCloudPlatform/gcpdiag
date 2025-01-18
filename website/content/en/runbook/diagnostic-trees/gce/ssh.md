---
title: "gce/Ssh"
linkTitle: "gce/ssh"
weight: 3
type: docs
description: >
  A comprehensive troubleshooting guide for common issues which affects SSH connectivity to VMs.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)
**Kind**: Debugging Tree

### Description

Investigates components required for ssh on either Windows and Linux VMs
  hosted on Google Cloud Platform and pinpoint misconfigurations.

  Areas Examined:

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

  - SSH in Browser Checks: Checks if the authenticated user has relevant permissions and
    the organization policies permits SSH in Browser.

### Executing this runbook

```shell
gcpdiag runbook gce/ssh \
  -p project_id=value \
  -p name=value \
  -p instance_name=value \
  -p instance_id=value \
  -p id=value \
  -p zone=value \
  -p principal=value \
  -p local_user=value \
  -p posix_user=value \
  -p tunnel_through_iap=value \
  -p proxy=value \
  -p check_os_login=value \
  -p client=value \
  -p src_ip=value \
  -p protocol_type=value \
  -p port=value \
  -p check_ssh_in_browser=value \
  -p access_method=value \
  -p mfa=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The ID of the project hosting the GCE VM |
| `name` | False | None | str | The name of the target GCE VM |
| `instance_name` | False | None | str | The name of the target GCE VM |
| `instance_id` | False | None | int | The instance ID of the target GCE VM |
| `id` | False | None | int | The instance ID of the target GCE VM |
| `zone` | True | None | str | The zone of the target GCE VM |
| `principal` | False | None | str | The user or service account initiating the SSH connection. This user should be authenticated in gcloud/cloud console when sshing into to a GCE instance. For service account impersonation, it should be the service account's email. (format: user:user@example.com or serviceAccount:service-account-name@project-id.iam.gserviceaccount.com) |
| `local_user` | False | None | str | Posix User on the VM |
| `posix_user` | False | None | str | Posix User on the VM |
| `tunnel_through_iap` | False | True | bool | ('A boolean parameter (true or false) indicating whether ', 'Identity-Aware Proxy should be used for establishing the SSH connection.') |
| `proxy` | False | None | str | ('A string that specifies the method used to establish the SSH connection, ', 'and indicating whether Identity-Aware Proxy (IAP) or a jumphost is utilized.') |
| `check_os_login` | False | True | bool | A boolean value (true or false) indicating whether OS Login should be used for SSH authentication |
| `client` | False | None | str | The SSH client used to establish SSH connection |
| `src_ip` | False | None | IPv4Address | Specify the IPv4 address of the workstation connecting to the network, or the IP of the bastion/jumphost if currently logged in through one. |
| `protocol_type` | False | tcp | str | Protocol used to connect to SSH |
| `port` | False | 22 | int | Specifies the port used to connect to on the remote host (default: 22) |
| `check_ssh_in_browser` | False | False | bool | Check that SSH in Browser is feasible |
| `access_method` | False | None | str | The method used to share or restrict access to the instance |
| `mfa` | False | None | str | Additional authentication features required to access to the instance |

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

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Os Login Status Check](/runbook/steps/gce/os-login-status-check)

  - [Iam Policy Check](/runbook/steps/iam/iam-policy-check)

  - [Gce Firewall Allows Ssh](/runbook/steps/gce/gce-firewall-allows-ssh)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Gce Vpc Connectivity Check](/runbook/steps/gce/gce-vpc-connectivity-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Vm Serial Logs Check](/runbook/steps/gce/vm-serial-logs-check)

  - [Ssh In Browser Check](/runbook/steps/gce/ssh-in-browser-check)

  - [Org Policy Check](/runbook/steps/crm/org-policy-check)

  - [Ssh End](/runbook/steps/gce/ssh-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
