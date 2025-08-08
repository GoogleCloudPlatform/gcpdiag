---
title: "bigquery/Check Bq Job Has Failed"
linkTitle: "Check Bq Job Has Failed"
weight: 3
type: docs
description: >
  Gateway to verify that a completed job contains an error result.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: GATEWAY

### Description

This step inspects the job details to see if an error was reported. If an
  error is present, the runbook proceeds to the final analysis step. If the job
  completed successfully, the runbook stops and informs the user.

### Failure Reason

Job successfully finished execution without any errors.

### Failure Remediation

Only failed BigQuery jobs can be analyzed for failure reasons. Restart the investigation and provide a job that failed during execution.

### Success Reason

Job finished execution with an error. Continuing the investigation.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
