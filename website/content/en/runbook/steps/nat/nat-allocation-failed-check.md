---
title: "nat/Nat Allocation Failed Check"
linkTitle: "Nat Allocation Failed Check"
weight: 3
type: docs
description: >
  Checks NAT Allocation failed metric for the NATGW.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

This step determines whether Cloud NAT has run into issues due to insufficient
  NAT IP addresses.
  by checking the NAT Allocation failed metric.

### Failure Reason

NAT IP allocation failure found on the NAT Gateway: {nat_gateway_name}

### Failure Remediation

Continue the runbook for further diagnostic and remediation steps for the
IP exhaustion issue on {nat_gateway_name}

### Success Reason

No issues noticed on the NAT allocation failed metric for the NAT Gateway: {nat_gateway_name}

### Uncertain Reason

Unable to fetch the the nat_allocation_failed metric for the gateway: {nat_gateway_name}

### Uncertain Remediation

Confirm that the NAT Gateway name {nat_gateway_name} provided is correct and
metric for the gateway is visible on cloud console.

### Skipped Reason

No issues detected on the nat_allocation_failed metric for the gateway: {nat_gateway_name}.
Checks on the status of the cloud router for the NAT gateway: {router_name} does not indicate
extra IPs are needed.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
