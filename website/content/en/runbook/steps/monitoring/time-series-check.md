---
title: "monitoring/Time Series Check"
linkTitle: "Time Series Check"
weight: 3
type: docs
description: >
  Assess if a given metric is has expected values..
---

**Product**: https://cloud.google.com/monitoring\
**Step Type**: AUTOMATED STEP

### Description

Currently checks if an attribute
  - Currently checks if metrics exists indicating a problem
  - Improve to be more flexible.

### Failure Reason

A known bad value is present within the checked metric collection.

### Failure Remediation

Review the metric data in Cloud Monitoring for more details.

Alternatively, run the following Cloud Logging query:

Query:
{query}

### Success Reason

The expected good value is present within the checked metric collection.

### Uncertain Reason

The metric data analysis was inconclusive. Manual investigation using Cloud Logging is recommended.

### Uncertain Remediation

Review the metric data in Cloud Monitoring for more details.

Alternatively, run the following Cloud Logging query:

Query:
{query}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
