---
title: "lb/Analyze Failed Caa Check"
linkTitle: "Analyze Failed Caa Check"
weight: 3
type: docs
description: >
  Analyzes domains in "FAILED_CAA_CHECKING" or "FAILED_CAA_FORBIDDEN" state.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

The following domains are in "FAILED_CAA_CHECKING" or "FAILED_CAA_FORBIDDEN" state: {domains}. This indicates misconfigured CAA records.  CAA records authorize specific Certificate Authorities to issue certificates for your domain.

### Failure Remediation

Please ensure the CAA records are configured correctly and try again. See the documentation for instructions on configuring CAA records: https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs#caa



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
