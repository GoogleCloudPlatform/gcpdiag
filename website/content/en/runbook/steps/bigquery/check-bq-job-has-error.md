---
title: "bigquery/Check Bq Job Has Error"
linkTitle: "Check Bq Job Has Error"
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

The completed job `{job_id}` finished successfully without any errors.

### Failure Remediation

This runbook is designed to analyze failed jobs. Please provide the ID of a job that has completed with an error.

### Success Reason

OK: The completed job `{job_id}` contains an error message, as expected for this analysis.
The error reported was: {error_string}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
