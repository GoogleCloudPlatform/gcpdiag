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

    The project {project_id} has BGP flaps with a duration over 60s.

### Failure Remediation

    Please continue to check router logging. Further debugging is needed.

### Success Reason

    No BGP flaps are found.

### Uncertain Reason

    There are BGP flaps with duration less than 60s.

### Uncertain Remediation

    Please continue to check if there are cloud router maintenance.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
