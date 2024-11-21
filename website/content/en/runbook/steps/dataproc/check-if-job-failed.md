---
title: "dataproc/Check If Job Failed"
linkTitle: "Check If Job Failed"
weight: 3
type: docs
description: >
  Verify if dataproc job failed.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Job {job_id} has completed successfully.

### Failure Remediation

The job you shared hasn't failed.
If your job experienced slow performance, potential causes could include data skew, changes in data volume, or network latency.
Please initiate a support case and share the Spark event log for both the fast and slow job runs.

### Success Reason

Job {job_id} was failed. Run the rest steps to investigate further.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
