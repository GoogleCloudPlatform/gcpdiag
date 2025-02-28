---
title: "dataproc/Check Master Oom"
linkTitle: "Check Master Oom"
weight: 3
type: docs
description: >
  Check if OOM has happened on master.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Found logs messages related to Master OOM on the cluster: {cluster_name}.

### Failure Remediation

Please follow the troubleshooting guide [1] to adjust the driver memory used for the job.

[1] <https://cloud.google.com/dataproc/docs/support/troubleshoot-oom-errors#oom_solutions>

### Success Reason

Didn't find logs messages related to Master OOM on the cluster: {cluster_name}.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
