---
title: "lb/Analyze Certificate Status"
linkTitle: "Analyze Certificate Status"
weight: 3
type: docs
description: >
  Analyze the status of the Google-managed certificate.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: GATEWAY

### Description

None

### Failure Reason

The Google-managed SSL certificate "{name}" is in the PROVISIONING_FAILED_PERMANENTLY state. This is a non-recoverable state.

### Failure Remediation

Recreate the certificate. Refer to the documentation for instructions on creating SSL certificates.

### Success Reason

The Google-managed SSL certificate "{name}" is in {status} state.

### Uncertain Reason

The Google-managed SSL certificate "{name}" is in the {status} state. {context}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
