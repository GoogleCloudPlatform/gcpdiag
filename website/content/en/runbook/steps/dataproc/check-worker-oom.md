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

The log indicates that worker OOM (out-of-memory) errors may have occurred on your cluster.
You can try using a high-memory machine type for your worker nodes or repartition your data to avoid data skew.

You can find more details in the troubleshooting guide [1].
If it still not work, please contact Google Cloud Support.
[1] <https://cloud.google.com/dataproc/docs/support/troubleshoot-oom-errors#oom_solutions>

### Success Reason

Didn't find logs messages related to Worker OOM on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
