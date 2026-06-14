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

    Attachment:{attachment_name}, Interconnect:{interconnect_name}, Cloud_Router_Name:{router_name}

### Failure Remediation

     For any interconnects in BGP down state, continue runbook check if the interconnect is in maintenance state. Check the public documentation for guidance. <https://cloud.google.com/network-connectivity/docs/interconnect/support/infrastructure-maintenance-events>

### Success Reason

    No VLAN attachments have BGP down in region `{region}` in project `{project_id}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
