---
title: "interconnect/Check Bgp Down"
linkTitle: "Check Bgp Down"
weight: 3
type: docs
description: >
  Check if vlan attachments have BGP down state.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any vlan attachments have in BGP down state.

### Failure Reason

    The interconnect `{interconnect_name}` attachment `{attachment_name}` has `BGP` down.

### Failure Remediation

     Check if interconnects with BGP down are in maintenance state. Analyze Cloud Router logs to identify the root cause. Refer to the Cloud Router log messages documentation for guidance. <https://cloud.google.com/network-connectivity/docs/interconnect/support/infrastructure-maintenance-events>

### Success Reason

    No `VLAN attachments` have `BGP` down.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
