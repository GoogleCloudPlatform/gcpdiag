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
