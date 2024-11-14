---
title: "lb/Lb Eror Rate Check"
linkTitle: "Lb Eror Rate Check"
weight: 3
type: docs
description: >
  Check if error exceeds the threshold
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The forwarding rule has a high error rate per minute in the last 15m {average_error_rate}

### Failure Remediation

Check the health of your backend and run the 5xx playbook

### Success Reason

The forwarding rule does not have a high average error rate per minute in the last 15m {average_error_count}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
