---
title: "nat/Public Nat Ip Allocation Failed"
linkTitle: "nat/public-nat-ip-allocation-failed"
weight: 3
type: docs
description: >
  Troubleshooting for IP Allocation issues for Cloud NAT.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)
**Kind**: Debugging Tree

### Description

This runbook investigates Cloud NAT for NAT IP Allocation failed issue and proposes
  remediation steps.

  Areas Examined:

    - Metric check: Checks the NAT Allocation Failed metric for the provided NATGW if it is
    True or False.

    - NATGW Configuration: Checks the gateway if it is configured with manual or automatic IP
    allocation.

    - NAT IP and Port calculation: For source nic without an External IP address,
      verify the VM is served by a Public NAT Gateway and check there are no issues on the NATGW.

### Executing this runbook

```shell
gcpdiag runbook nat/public-nat-ip-allocation-failed \
  -p project_id=value \
  -p nat_gateway_name=value \
  -p cloud_router_name=value \
  -p network=value \
  -p nat_network=value \
  -p region=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `nat_gateway_name` | True | None | str | The name of the NATGW |
| `cloud_router_name` | True | None | str | The name of the Cloud Router of the NATGW |
| `network` | False | None | str | The VPC network of the target NATGW |
| `nat_network` | True | None | str | The VPC network of the target NATGW |
| `region` | True | None | str | The region of the target NATGW |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Nat Ip Allocation Failed Start](/runbook/steps/nat/nat-ip-allocation-failed-start)

  - [Nat Allocation Failed Check](/runbook/steps/nat/nat-allocation-failed-check)

  - [Nat Ip Allocation Method Check](/runbook/steps/nat/nat-ip-allocation-method-check)

  - [Nat Ip Allocation Auto Only](/runbook/steps/nat/nat-ip-allocation-auto-only)

  - [Nat Ip Allocation Manual Only](/runbook/steps/nat/nat-ip-allocation-manual-only)

  - [Nat Ip Allocation Failed End](/runbook/steps/nat/nat-ip-allocation-failed-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
