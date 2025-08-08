---
title: "lb/Lb Request Count Check"
linkTitle: "Lb Request Count Check"
weight: 3
type: docs
description: >
  Check if request count per second exceeds the threshold
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The forwarding rule has an average request count of {average_request_count} requests/s in the last 15 minutes. This is higher than the threshold value of {threshold}.

### Failure Remediation

The high request count suggests the backend may be overloaded. Consider scaling up the backend by adding more instances or increasing the resources of existing instances.

### Success Reason

The forwarding rule has an average request count of {average_request_count} requests/s in the last 15 minutes. This is less than the threshold value of {threshold}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
