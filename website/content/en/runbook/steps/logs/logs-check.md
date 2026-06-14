---
title: "logs/Logs Check"
linkTitle: "Logs Check"
weight: 3
type: docs
description: >
  Assess if a given log query is present or not..
---

**Product**: [Cloud Logging](https://cloud.google.com/logging)\
**Step Type**: AUTOMATED STEP

### Description

Checks if a log attribute has a bad or good pattern

### Failure Reason

A known bad value is present within the checked log entry indicating a problem

### Failure Remediation

Run the following Cloud Logging query in the Google Cloud console to find the log entry indicating the problem:

Query:
{query}

### Success Reason

The expected good value is present within the checked log entry.

### Uncertain Reason

The outcome could not be determined automatically. Manually verify the relevant details in [Cloud Logging](https://cloud.google.com/logging).

### Uncertain Remediation

Run the following Cloud Logging query in the Google Cloud console to manually review the relevant log entries:

Query:
{query}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
