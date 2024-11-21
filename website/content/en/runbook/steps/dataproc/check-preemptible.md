---
title: "dataproc/Check Preemptible"
linkTitle: "Check Preemptible"
weight: 3
type: docs
description: >
  Verify preemptibility.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Cluster {cluster.name} uses preemptible workers and their count exceeds 50% of the total worker count leading to shuffle fetch failures.

### Failure Remediation

Consider reducing the number of preemptible workers or using non-preemptible workers for better stability.
You may also explore Enhanced Flexibility Mode (EFM) for better control over preemptible instances.

### Success Reason

Cluster {cluster.name} uses preemptible workers. While within the recommended limit, preemptions might still lead to FetchFailedExceptions.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
