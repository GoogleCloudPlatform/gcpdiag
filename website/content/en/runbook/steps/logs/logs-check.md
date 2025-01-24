---
title: "logs/Logs Check"
linkTitle: "Logs Check"
weight: 3
type: docs
description: >
  Assess if a given log query is present or not..
---

**Product**: \
**Step Type**: AUTOMATED STEP

### Description

Checks if a log attribute has a bad or good pattern

### Failure Reason

A known bad value is present within the checked log entry indicating a problem

### Failure Remediation

View Cloud logging to get more details of how to what is causing this issue.

Run the following cloud logging query in GCP.

Query:
{query}

### Success Reason

The expected good value is present within the checked log entry.

### Uncertain Reason

The outcome could not be determined automatically. Please manually verify the relevant details in [Cloud Logging](https://cloud.google.com/logging).

### Uncertain Remediation

View Cloud logging to get more details of how to what is causing this issue.

Run the following cloud logging query in GCP.

Query:
{query}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
