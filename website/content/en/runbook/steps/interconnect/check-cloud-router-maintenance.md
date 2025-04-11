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

    There are BGP flaps less than 60s without Cloud Router maintenance events.

### Failure Remediation

    Please continue to check router logging. Further debugging is needed.

### Success Reason

    BGP flaps less than 60s are all caused by Cloud Router maintenance events.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
