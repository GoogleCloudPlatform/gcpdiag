---
title: "interconnect/Check Interconnect Maintenance"
linkTitle: "Check Interconnect Maintenance"
weight: 3
type: docs
description: >
  Check if interconnects with BGP down are in maintenance state.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any interconnects with BGP down are in maintenance state.

### Failure Reason

    The interconnect `{interconnect_name}` with BGP down status has no planned maintenance.

### Failure Remediation

    Interconnect BGP down can be caused by various reasons. Suggested remediation: {remediation}

### Success Reason

    The interconnects with BGP down status align with the planned interconnect maintenance events.

### Skipped Reason

    No interconnects have BGP down status, skip interconnect mainteance check in in region `{region}` in project `{project_id}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
