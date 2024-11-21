---
title: "nat/Nat Dropped Received Packet Check"
linkTitle: "Nat Dropped Received Packet Check"
weight: 3
type: docs
description: >
  Evaluates NATGW received_packets_dropped metric for issues.
---

**Product**: [Cloud NAT](https://cloud.google.com/nat)\
**Step Type**: AUTOMATED STEP

### Description

This step determines whether the NATGW is dropping packets. NAT gateways could be dropping
  packets for various reasons; however, the drops are not always indicative of an issue

### Success Reason

   No received_packet_drop on NAT GW {nat_gateway_name} seen.

### Uncertain Reason

   Elevated received_packet_drop_count metric noticed for NAT GW {nat_gateway_name}
   dropped_received_packet: {metric_value}

### Uncertain Remediation

   NAT gateways could be dropping packets for various reasons; however, the drops are not always indicative of an issue.
   Checking received_packet_drop metrics at the VM level as well. Open a case to GCP Support for confirmation
   of the reason for the drops
   See more on troubleshooting cloud NAT reducing the drops here [1] and [2]:
   [1] https://cloud.google.com/nat/docs/troubleshooting
   [2] https://cloud.google.com/knowledge/kb/reduce-received-packets-dropped-count-on-cloud-nat-000006744



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
