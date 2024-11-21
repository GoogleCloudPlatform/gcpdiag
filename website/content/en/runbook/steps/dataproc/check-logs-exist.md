---
title: "dataproc/Check Logs Exist"
linkTitle: "Check Logs Exist"
weight: 3
type: docs
description: >
  Checks if specified logs messages exist in the Dataproc cluster.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

This step supports checking for the presence of a concrete log message.

  Attributes:
    log_message (str): log message that is being looked for.

### Failure Reason

Found logs messages related to "{log}" on the cluster: {cluster_name}.

### Failure Remediation

Please investigate further the job logs by focusing on eliminating the observed message.

### Success Reason

Didn't find logs messages related to "{log}" on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
