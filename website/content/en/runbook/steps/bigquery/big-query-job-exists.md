---
title: "bigquery/Big Query Job Exists"
linkTitle: "Big Query Job Exists"
weight: 3
type: docs
description: >
  Gateway that verifies the BigQuery Job exists.
---

**Product**: [BigQuery](https://cloud.google.com/bigquery)\
**Step Type**: GATEWAY

### Description

This step calls the BigQuery API to fetch the job. If the job is found, the
  runbook proceeds to the next step. If it is not found (e.g., due to a typo in
  the job ID or region), the runbook reports this and terminates this path.

### Failure Reason

Job {job_id} does not exist.

### Failure Remediation

Please check the corresponding job Region and make sure to provide the correct Job and Project identifiers.

### Success Reason

Job {job_id} was successfully located.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
