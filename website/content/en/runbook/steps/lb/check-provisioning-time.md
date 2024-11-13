---
title: "lb/Check Provisioning Time"
linkTitle: "Check Provisioning Time"
weight: 3
type: docs
description: >
  Checks if the SSL certificate associated resources has been updated recently.
---

**Product**: [Load balancing](https://cloud.google.com/load-balancing)\
**Step Type**: AUTOMATED STEP

### Description

None

### Success Reason

We haven't found any recent changes to the forwarding rules and target proxies associated with the certificate {name}.

### Uncertain Reason

The certificate {name} has recently had associated resources modified. This might affect DNS validation. Details are below:
{recently_changed}

### Uncertain Remediation

DNS validation automatically checks your domain's A and AAAA records against your Google Cloud load balancer's IP address. This process includes an automatic retry mechanism with increasing wait times. If you recently attached {name} to a target proxy or the target proxy to forwarding rule, validation could take up to 24 hours to complete.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->