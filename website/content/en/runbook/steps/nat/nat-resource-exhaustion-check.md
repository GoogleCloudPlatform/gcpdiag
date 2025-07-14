---
title: "nat/Nat Resource Exhaustion Check"
linkTitle: "Nat Resource Exhaustion Check"
weight: 3
type: docs
description: >
  Evaluates NATGW for OUT_OF_RESOURCES and ENDPOINT_INDEPENDENCE_CONFLICT issues.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

This step determines whether Cloud NAT has run into resource issues.

### Failure Reason

   {metric_reason} issue found on the dropped_sent_packet metric on the NAT GW {nat_gateway_name}

### Failure Remediation

   Resource exhaustion issues can be remediated by taking the following steps in [1]:
   [1] <https://cloud.google.com/knowledge/kb/cloud-nat-is-dropping-or-limiting-egress-connectivity-000004263#:~:text=If%20the%20metric%20indicates%20that,on%20the%20Port%20reservation%20procedure>

### Success Reason

   No {metric_reason} issues on the dropped_sent_packet metric for the NAT GW {nat_gateway_name} seen.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
