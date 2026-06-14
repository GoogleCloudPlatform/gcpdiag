---
title: "bigquery/Big Query Error Identification"
linkTitle: "Big Query Error Identification"
weight: 3
type: docs
description: >
  Analyzes the job's error message to find a known mitigation.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: AUTOMATED STEP

### Description

This is the final diagnostic step. It collects all error messages from the job
  and compares them against a dictionary of known issues (the ERROR_MAP). If a
  match is found, it provides a specific cause and remediation. Otherwise, it
  reports the full error for manual inspection.

### Failure Reason

Job failed with error: {error_message}

Job failure cause: {cause}

### Failure Remediation

Suggested mitigation: {remediation}

### Uncertain Reason

Job {job_id} failed with an error that does not have a publicly documented mitigation and root cause.
Full error message(s) reported:
"{error_message}"

### Uncertain Remediation

Please retry the job to confirm whether the error is transient and can be mitigated through a retry with exponential backoff. See <https://cloud.google.com/bigquery/docs/error-messages>.
If the issue persists, contact Google Cloud Support at <https://cloud.google.com/support> and provide this report with the full BigQuery Job Id.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
