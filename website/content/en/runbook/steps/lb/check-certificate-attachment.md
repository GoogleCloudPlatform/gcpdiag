---
title: "lb/Check Certificate Attachment"
linkTitle: "Check Certificate Attachment"
weight: 3
type: docs
description: >
  Check if the SSL certificate is attached to a target proxy.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: GATEWAY

### Description

This target proxy needs to be in use by a forwarding rule for the provisioning
  to succeed.

### Failure Reason

The SSL certificate "{name}" is not attached to any target proxies. Attach the certificate to a target proxy.

### Failure Remediation

Follow the documentation to attach the certificate to a target proxy: <https://cloud.google.com/load-balancing/docs/ssl-certificates/google-managed-certs#load-balancer>

### Success Reason

The SSL certificate "{name}" is attached to target proxies ({target_proxies}) that are in use by forwarding rules.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
