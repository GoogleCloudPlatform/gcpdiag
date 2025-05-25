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

    Check `router logging` for details.

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
