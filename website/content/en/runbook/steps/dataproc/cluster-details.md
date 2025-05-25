---
title: "dataproc/Cluster Details"
linkTitle: "Cluster Details"
weight: 3
type: docs
description: >
  Gathers cluster parameters needed for further investigation.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

Additional parameters are needed for next steps. If values are provided
  manually they will be used instead of values gathered here.

### Success Reason

Stackdriver: Enabled

### Uncertain Reason

Could not determine if the `dataproc:dataproc.logging.stackdriver.enable` property is enabled for cluster, possibly because the cluster was deleted. Subsequent checks requiring Stackdriver logging might be affected.

### Uncertain Remediation

Enable Stackdriver by creating a cluster with property dataproc:dataproc.logging.stackdriver.enable = true.
Refer to the guide for more details:
<https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
