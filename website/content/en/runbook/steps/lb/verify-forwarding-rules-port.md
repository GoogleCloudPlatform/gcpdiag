---
title: "lb/Verify Forwarding Rules Port"
linkTitle: "Verify Forwarding Rules Port"
weight: 3
type: docs
description: >
  Checks if the load balancer is configured to listen on port 443.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

More specifically, check if all IP addresses associated with the certificate
  have forwarding rules that listen on port 443

### Failure Reason

{misconfigured_entities}
There must be at least one load balancer's forwarding rule that use TCP port 443 for the Google-managed certificate to be initially provisioned and automatically renewed.

### Failure Remediation

Configure the load balancer to listen on port 443 for SSL certificate "{name}".

### Success Reason

The SSL certificate "{name}" has forwarding rules configured for HTTPS (port 443) on all associated IP addresses.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
