---
title: "interconnect/Check Cloud Router Maintenance"
linkTitle: "Check Cloud Router Maintenance"
weight: 3
type: docs
description: >
  Check if any Cloud Router had maintenance event.
---

**Product**: [Interconnect](https://cloud.google.com/network-connectivity/docs/interconnect)\
**Step Type**: AUTOMATED STEP

### Description

Check if any Cloud Router had maintenance event.
  Report BGP flaps without Cloud Router maintenance event.

### Failure Reason

    `BGP` flaps (duration < 60s) detected that do not coincide with `Cloud Router maintenance` events.

### Failure Remediation

    BGP flaps lasting less than 60 seconds have been observed. No associated Cloud Router or Interconnect maintenance events could be found. Analyze Cloud Router logs to identify the root cause. Refer to the Cloud Router log messages documentation for guidance. <https://cloud.google.com/network-connectivity/docs/router/support/troubleshoot-log-messages>

### Success Reason

    `BGP` flaps (duration < 60s) coincide with `Cloud Router maintenance` events.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
