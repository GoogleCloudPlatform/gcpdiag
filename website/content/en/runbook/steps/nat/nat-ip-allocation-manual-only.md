---
title: "nat/Nat Ip Allocation Manual Only"
linkTitle: "Nat Ip Allocation Manual Only"
weight: 3
type: docs
description: >
  Investigates when NAT IP allocation is MANUAL_ONLY.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

If the NAT IP allocation is configured as MANUAL_ONLY:
    - Confirm if the number of NAT IP's required by the gateway is over 300
    - Follow the NAT IP Quota Incrase Process

### Failure Reason

    The number of NAT IPs in use on the NAT Gateway is >= 300 which is above the quota limit [1].

      1. https://cloud.google.com/nat/quota#quotas

### Failure Remediation

    Consider creating additional NAT gateways or optimise port usage [1]:

    1. https://cloud.google.com/nat/docs/troubleshooting#reduce-ports

### Success Reason

    Checking on the status and configuration of the Cloud NAT Router {router_name} and Gateway:

       1. Minimum extra NAT IPs Needed: {extra_ips_needed}
       2. Number of VM Endpoints With NAT mappings: {vms_with_nat_mappings}
       3. Dynamic port allocation enabled: {enable_dynamic_port_allocation}
       4. Number of NAT Gateway IPs in use: {nat_gw_ips_in_use}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
