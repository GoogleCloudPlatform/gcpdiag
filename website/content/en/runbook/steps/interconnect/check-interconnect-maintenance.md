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

    The interconnect `{interconnect_name}` with `BGP` down has no planned maintenance.

### Failure Remediation

    Analyze Cloud Router logs to identify the root cause. Refer to the Cloud Router log messages documentation for guidance. <https://cloud.google.com/network-connectivity/docs/router/support/troubleshoot-log-messages>

### Success Reason

    `BGP` down events coincide with planned interconnect maintenance.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
