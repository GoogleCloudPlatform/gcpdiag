---
title: "dataflow/Job State"
linkTitle: "Job State"
weight: 3
type: docs
description: >
  Has common step to check job state is not failed.
---

**Product**: [Dataflow](https://cloud.google.com/dataflow)\
**Step Type**: AUTOMATED STEP

### Description

Usually the specific error is logged in the Dataflow Monitoring Interface.

### Failure Reason

  Job State for job {job_id} is Failed.

### Failure Remediation

  Check Dataflow Monitoring Interface for the specific error, and find the error among
  common errors here[1] to resolve the job errors.

  [1] https://cloud.google.com/dataflow/docs/guides/common-errors#pipeline_errors

### Success Reason

   Job State is successfully {state}



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
