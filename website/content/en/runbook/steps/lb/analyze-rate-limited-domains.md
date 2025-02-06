---
title: "lb/Analyze Rate Limited Domains"
linkTitle: "Analyze Rate Limited Domains"
weight: 3
type: docs
description: >
  Analyze domains in "FAILED_RATE_LIMITED" state.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The following domains are in FAILED_RATE_LIMITED state: {domains} for SSL certificate "{name}". This indicates rate limiting by the Certificate Authority.  You've likely exceeded the allowed number of certificate requests in a short period.

### Failure Remediation

Wait for a while and then check the certificate status again. If the issue persists, contact Google Cloud Support.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
