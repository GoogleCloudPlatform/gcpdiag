---
title: "nat/Nat Ip Allocation Auto Only"
linkTitle: "Nat Ip Allocation Auto Only"
weight: 3
type: docs
description: >
  Provides recommendations when NAT IP allocation is AUTO_ONLY.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

NAT IP allocation is configured as AUTO_ONLY, either:
    - Switch to Manual NAT IP assignment or
    - Add one more gateway in the same network and region

### Failure Reason

The NAT Gateway {nat_gateway_name} is configured for automatic IP allocation

### Failure Remediation

To resolve this issue, consider implementing the following options:

1. Add one more NAT gateway in the same network and region.
2. Switch to Manual NAT IP assignment.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
