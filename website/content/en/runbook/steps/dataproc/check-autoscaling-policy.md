---
title: "dataproc/Check Autoscaling Policy"
linkTitle: "Check Autoscaling Policy"
weight: 3
type: docs
description: >
  Verify autoscaling policies.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

None

### Failure Reason

Autoscaling is enabled without graceful decommission timeout on cluster {cluster_name}

### Failure Remediation

Enable graceful decommission timeout in the autoscaling policy to allow executors to fetch shuffle data before nodes are removed.



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
