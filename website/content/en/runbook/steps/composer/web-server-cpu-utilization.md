---
title: "composer/Web Server Cpu Utilization"
linkTitle: "Web Server Cpu Utilization"
weight: 3
type: docs
description: >
  Check the CPU utilization of the Composer environment's web server.
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

This step queries the Kubernetes API to see if the web server pod has high
  CPU utilization.

### Failure Reason

Web Server CPU utilization is at or near its limit.

### Failure Remediation

Consider increasing the CPU limit for the web server.

### Success Reason

Web server CPU utilization is normal.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
