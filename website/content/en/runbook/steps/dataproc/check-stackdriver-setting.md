---
title: "dataproc/Check Stackdriver Setting"
linkTitle: "Check Stackdriver Setting"
weight: 3
type: docs
description: >
  Check if Stackdriver is enabled for the cluster.
---

**Product**: [Cloud Dataproc](https://cloud.google.com/dataproc)\
**Step Type**: AUTOMATED STEP

### Description

If the property is provided manually, It will be used if
  the cluster does not exist.

### Success Reason

Stackdriver: Enabled

### Uncertain Reason

Could not determine if the `dataproc:dataproc.logging.stackdriver.enable` property is enabled for cluster, possibly because the cluster was deleted. Subsequent checks requiring Cloud logging might be affected.

### Uncertain Remediation

Enable Cloud logging by creating a cluster with property dataproc:dataproc.logging.stackdriver.enable = true.
Refer to the guide for more details:
<https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties>



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
