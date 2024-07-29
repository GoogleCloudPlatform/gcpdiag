---
title: "composer/Log Based Checks"
linkTitle: "Log Based Checks"
weight: 3
type: docs
description: >
  The LogBasedChecks class is a designed to scrutinize (GCP) logs for
---

**Product**: [Cloud Composer](https://cloud.google.com/composer)\
**Step Type**: AUTOMATED STEP

### Description

specific operational issues.

  It primarily checks for:

  Org Policy Violations: It examines logs for instances where organizational
  policies, such as those related to compute instance configuration (e.g.,
  serial port logging, OS login, IP forwarding), have been breached.

  Managed Instance Group Quota Issues: It investigates whether any logs indicate
  that the project has exceeded its allocated quota for creating managed
  instance groups.

  The class provides structured output, adding success messages if no issues are
  found and failure messages with remediation suggestions if problems are
  detected. This aids in automating the monitoring and troubleshooting of common
  GCP operational challenges.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
