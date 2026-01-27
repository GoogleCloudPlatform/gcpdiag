---
title: "vpn/Vpn Tunnel Check"
linkTitle: "vpn/vpn-tunnel-check"
weight: 3
type: docs
description: >
  Runbook for diagnosing issues with a Cloud VPN Tunnel.
---

**Product**: [Vpn](https://cloud.google.com/hybrid-connectivity)
**Kind**: Debugging Tree

### Description

This runbook performs several checks on a specified Cloud VPN tunnel:
-   **VPN Tunnel Status Check**: Verifies if the VPN tunnel is in an
    'ESTABLISHED' state.
-   **Tunnel Down Status Reason**: If the tunnel is not established, it queries
    Cloud Logging for specific error messages and provide remediations .
-   **Tunnel Packet Drop Check**: If the tunnel is established, it examines
    monitoring metrics for various types of packet drops (e.g., due to MTU,
    invalid SA, throttling) and provides remediation based on the drop reason.
-   **Tunnel Packet Utilization Check**: Analyzes packet rates to identify if
    the tunnel is hitting max packet per second limits.

### Executing this runbook

```shell
gcpdiag runbook vpn/vpn-tunnel-check \
  -p project_id=value \
  -p region=value \
  -p name=value \
  -p start_time=value \
  -p end_time=value \
  -p tunnel=value
```

#### Parameters

| Name | Required | Default | Type | Help |
|------|----------|---------|------|------|
| `project_id` | True | None | str | The Project ID of the resource under investigation |
| `region` | True | None | str | The region where the VPN Tunnel is located |
| `name` | True | None | str | Name of the VPN Tunnel |
| `start_time` | False | None | datetime | The start window to investigate BGP flap. Format: YYYY-MM-DDTHH:MM:SSZ |
| `end_time` | False | None | datetime | The end window for the investigation. Format: YYYY-MM-DDTHH:MM:SSZ |
| `tunnel` | False | None | str | This Flag will be added Automatically |

Get help on available commands

```shell
gcpdiag runbook --help
```

### Potential Steps

  - [Vpn Tunnel Status](/runbook/steps/vpn/vpn-tunnel-status)

  - [Tunnel Down Status Reason](/runbook/steps/vpn/tunnel-down-status-reason)

  - [Tunnel Packets Drop Check](/runbook/steps/vpn/tunnel-packets-drop-check)

  - [Tunnel Packets Utilization Check](/runbook/steps/vpn/tunnel-packets-utilization-check)

  - [Vpn Tunnel Check End](/runbook/steps/vpn/vpn-tunnel-check-end)


<!--
This file is auto-generated. DO NOT EDIT.
-->
