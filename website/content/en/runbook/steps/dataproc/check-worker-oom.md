---
title: "dataproc/Check Worker Oom"
linkTitle: "Check Worker Oom"
weight: 3
type: docs
description: >
  Verify if OOM has happened on worker nodes.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Found logs messages related to Worker OOM on the cluster: {cluster_name}.

### Failure Remediation

The logs indicate that worker OOM (out-of-memory) errors may have occurred on the cluster.
To resolve this issue:

- Use a high-memory machine type for the worker nodes.
- Repartition the data to avoid data skew.

Refer to the troubleshooting guide [1] for more details.
If the issue persists, contact Google Cloud Support.
[1] <https://cloud.google.com/dataproc/docs/support/troubleshoot-oom-errors#oom_solutions>

### Success Reason

Didn't find logs messages related to Worker OOM on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
