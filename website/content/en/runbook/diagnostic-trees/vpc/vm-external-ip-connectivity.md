---
title: "vpc/Vm External Ip Connectivity"
linkTitle: "vpc/vm-external-ip-connectivity"
weight: 3
type: docs
description: >
  Troubleshooting for common issues which affect VM connectivity to external IP addresses.
---

**Product**: [Virtual Private Cloud](https://cloud.google.com/vpc)
**Kind**: Debugging Tree

### Description

This runbook investigates components required for VMs to establish connectivity
  to external IP addresses

  Areas Examined:

  - VM Instance:
      - Verify that the VM exists and is running

  - VM Configuration:
      - Checks the source nic configuration on the VM if it has an
        External IP address or not.

  - VPC routes checks:
      - Checks the VPC routing rules are configured to allow external connectivity

  - VPC firewall and firewall policy checks:
      - Checks the VPC firewall and firewall policies allow external connectivity.

  - GCE Network Connectivity Tests:
      - Runs a VPC network connectivity test and reports the result.

  - NATGW Checks:
      - For source nics without an External IP address, verify the VM is served
        by a Public NAT Gateway and check there are no issues on the NATGW.

### Executing this runbook

```shell
gcpdiag runbook vpc/vm-external-ip-connectivity \
  -p project_id=value \
  -p name=value \
  -p instance_name=value \
  -p dest_ip=value \
  -p dest_port=value \
  -p protocol_type=value \
  -p src_nic=value \
  -p zone=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `name` | False | None | str | The name of the GCE Instance |
| `instance_name` | True | None | str | The name of the GCE Instance |
| `dest_ip` | True | None | IPv4Address | External IP the VM is connecting to |
| `dest_port` | False | 443 | int | External IP the VM is connecting to |
| `protocol_type` | False | tcp | str | Protocol used to connect to SSH |
| `src_nic` | True | None | str | VM source NIC |
| `zone` | True | None | str | The zone of the target GCE Instance |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Vm External Ip Connectivity Start](/runbook/steps/vpc/vm-external-ip-connectivity-start)

  - [Service Api Status Check](/runbook/steps/gcp/service-api-status-check)

  - [Vm Has External Ip](/runbook/steps/vpc/vm-has-external-ip)

  - [External Interface Check](/runbook/steps/vpc/external-interface-check)

  - [Internal Interface Check](/runbook/steps/vpc/internal-interface-check)

  - [Vm External Ip Connectivity End](/runbook/steps/vpc/vm-external-ip-connectivity-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
