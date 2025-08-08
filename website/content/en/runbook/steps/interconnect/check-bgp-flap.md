---
title: "interconnect/Check Bgp Flap"
linkTitle: "Check Bgp Flap"
weight: 3
type: docs
description: >
  Check if any BGP flap events, report error flaps with duration over 60 seconds.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any BGP flap events, report error flaps with duration over 60 seconds.

### Failure Reason

    `BGP` flaps lasting longer than 60 seconds detected in project `{project_id}`.

### Failure Remediation

    BGP flaps lasting longer than 60 seconds have been observed. These are unlikely to be caused by Cloud Router or Interconnect maintenance events. Analyze Cloud Router logs to identify the root cause. Refer to the Cloud Router log messages documentation for guidance.<https://cloud.google.com/network-connectivity/docs/router/support/troubleshoot-log-messages>

### Success Reason

    No `BGP` flaps are found.

### Uncertain Reason

    `BGP` flaps lasting less than 60 seconds detected.

### Uncertain Remediation

    Check for `cloud router maintenance` events.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
