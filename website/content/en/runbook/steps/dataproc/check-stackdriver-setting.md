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

Unable to find sufficient information if stackdriver.logging property is enabled. This may be due to the fact that the
cluster is deleted. The runbook will assume that it is enabled, however if not, it might affect some of the runbooks steps.

### Uncertain Remediation

Consider enabling it by creating a cluster with property dataproc:dataproc.logging.stackdriver.enable = true
Review our guide for more details:
https://cloud.google.com/dataproc/docs/concepts/configuring-clusters/cluster-properties



<!--
This file is auto-generated. DO NOT EDIT

Make pages changes in the corresponding jinja template
or python code
-->
