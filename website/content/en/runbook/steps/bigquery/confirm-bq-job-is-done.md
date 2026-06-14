---
title: "bigquery/Confirm Bq Job Is Done"
linkTitle: "Confirm Bq Job Is Done"
weight: 3
type: docs
description: >
  Gateway to confirm that the BigQuery job has finished execution.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: GATEWAY

### Description

This step checks the job's status. If the status is 'DONE', the runbook
  continues to the next check. If the job is still 'RUNNING' or 'PENDING', the
  runbook will stop and advise the user to wait for completion.

### Failure Reason

Job {job_id} is currently in the {job_state} state and has not yet completed.

### Failure Remediation

Wait for the job to finish execution and restart the investigation.

### Success Reason

Job {job_id} has finished execution.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
