---
title: "nat/Nat Ip Exhaustion Check"
linkTitle: "Nat Ip Exhaustion Check"
weight: 3
type: docs
description: >
  Evaluates NATGW for NAT IP exhaustion/allocation issues.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

This step determines whether Cloud NAT has run into issues due to insufficient NAT IP addresses.

### Failure Reason

   NAT IP allocation failure found on the NAT GW {nat_gateway_name}

### Failure Remediation

   IP exhaustion issues on {nat_gateway_name} can be remediated by taking the following steps in [1]:
   [1] <https://cloud.google.com/knowledge/kb/cloud-nat-is-dropping-or-limiting-egress-connectivity-000004263#:~:text=If%20the%20metric%20indicates%20that,on%20the%20Port%20reservation%20procedure>

### Success Reason

   No IP exhaustion issues found on the NAT GW {nat_gateway_name}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
