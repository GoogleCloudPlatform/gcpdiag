---
title: "dataproc/Job Exists"
linkTitle: "Job Exists"
weight: 3
type: docs
description: >
  Prepares the parameters required for the dataproc/spark_job_failures runbook.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: START

### Description

Ensures both project_id, region and job_id parameters are available.

### Failure Reason

The job `{job_id}` does not exist in project `{project_id}`.

### Failure Remediation

Verify that the job ID and region are correct.

### Success Reason

The job `{job_id}` exists in project `{project_id}`.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
