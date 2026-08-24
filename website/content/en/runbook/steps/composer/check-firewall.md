---
title: "composer/Check Firewall"
linkTitle: "Check Firewall"
weight: 3
type: docs
description: >
  Check for Firewall rules blocking Redis traffic.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Detected firewall denials on port 6379.

### Failure Remediation

Verify VPC firewall rules to allow ingress traffic from GKE secondary pod IP range to Redis service.

### Success Reason

No firewall issues detected.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
