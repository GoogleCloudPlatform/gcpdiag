---
title: "gce/Gce Firewall Allows Ssh"
linkTitle: "Gce Firewall Allows Ssh"
weight: 3
type: docs
description: >
  Assesses the VPC network configuration to ensure it allows SSH traffic to the target VM.
---

**Product**: [Compute Engine](https://cloud.google.com/compute)\
**Step Type**: COMPOSITE STEP

### Description

This diagnostic step checks for ingress firewall rules that permit SSH traffic based on
  the operational context, such as the use of IAP for SSH or direct access from a specified
  source IP. It helps identify network configurations that might block SSH connections.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
