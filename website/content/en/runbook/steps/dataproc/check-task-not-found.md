---
title: "dataproc/Check Task Not Found"
linkTitle: "Check Task Not Found"
weight: 3
type: docs
description: >
  Verify if dataproc job failed due to task not found.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: COMPOSITE STEP

### Description

None

### Failure Reason

Job {job_id} was failed due to 'task not found' error. {additional_message}

### Failure Remediation

This typically indicates the associated cluster was terminated prior to job completion.
Please review your automation workflows to ensure clusters remain active until all jobs are finalized.

### Success Reason

Job {job_id} didn't failed due to 'task not found' error. {additional_message}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
